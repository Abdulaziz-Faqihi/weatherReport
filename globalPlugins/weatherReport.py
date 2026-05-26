import globalPluginHandler
from scriptHandler import script
import ui
import config
import gui
import urllib.request
import urllib.parse
import json
import os
import threading
import wx

CONFIG_DIR = os.path.join(config.getUserDefaultConfigPath(), "weatherReport")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

DEFAULT_SETTINGS = {
	# Legacy single-location keys, kept for backward compatibility / migration.
	"latitude": None,
	"longitude": None,
	"city": "",
	# Multiple saved locations. Each is {name, label, latitude, longitude}.
	# current_index points at the location used for weather announcements.
	"locations": [],
	"current_index": 0,
	# Announcement preferences
	"announce_fetching": False,
	"show_feels_like": True,
	"show_humidity": True,
	"show_wind_kmh": True,
	"show_wind_ms": False,
	"show_uv_index": False,
	"show_visibility": False,
	"show_sunrise_sunset": False,
}

# Open-Meteo "current" gives temp, humidity, apparent temp, wind, weather code, day/night.
# UV index and visibility are only available per-hour, so we also request them hourly
# and pick the value matching the current hour. Sunrise/sunset come from the daily block.
API_URL = (
	"https://api.open-meteo.com/v1/forecast"
	"?latitude={lat}&longitude={lon}"
	"&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,weather_code,wind_speed_10m"
	"&hourly=uv_index,visibility"
	"&daily=sunrise,sunset"
	"&timezone=auto&forecast_days=1"
)

# Open-Meteo geocoding: turn a place name into matching locations with coordinates.
GEOCODE_URL = (
	"https://geocoding-api.open-meteo.com/v1/search"
	"?name={name}&count=10&language=en&format=json"
)

WMO_CODES = {
	0: "Clear sky",
	1: "Mainly clear",
	2: "Partly cloudy",
	3: "Overcast",
	45: "Foggy",
	48: "Depositing rime fog",
	51: "Light drizzle",
	53: "Moderate drizzle",
	55: "Dense drizzle",
	56: "Light freezing drizzle",
	57: "Dense freezing drizzle",
	61: "Slight rain",
	63: "Moderate rain",
	65: "Heavy rain",
	66: "Light freezing rain",
	67: "Heavy freezing rain",
	71: "Slight snowfall",
	73: "Moderate snowfall",
	75: "Heavy snowfall",
	77: "Snow grains",
	80: "Slight rain showers",
	81: "Moderate rain showers",
	82: "Violent rain showers",
	85: "Slight snow showers",
	86: "Heavy snow showers",
	95: "Thunderstorm",
	96: "Thunderstorm with slight hail",
	99: "Thunderstorm with heavy hail",
}


def loadSettings():
	settings = dict(DEFAULT_SETTINGS)
	if os.path.isfile(CONFIG_FILE):
		try:
			with open(CONFIG_FILE, "r", encoding="utf-8") as f:
				loaded = json.load(f)
			if isinstance(loaded, dict):
				settings.update(loaded)
		except Exception:
			pass
	# Migrate an older single-location config into the new locations list.
	if not settings.get("locations") and settings.get("latitude") is not None and settings.get("longitude") is not None:
		name = settings.get("city", "") or ""
		settings["locations"] = [{
			"name": name,
			"label": name or f"{settings['latitude']}, {settings['longitude']}",
			"latitude": settings["latitude"],
			"longitude": settings["longitude"],
		}]
		settings["current_index"] = 0
	return settings


def saveSettings(settings):
	os.makedirs(CONFIG_DIR, exist_ok=True)
	with open(CONFIG_FILE, "w", encoding="utf-8") as f:
		json.dump(settings, f, indent="\t", ensure_ascii=False)


def _currentLocation(settings):
	"""Return the currently selected location dict, or None if none is set."""
	locations = settings.get("locations", [])
	idx = settings.get("current_index", 0)
	if isinstance(locations, list) and isinstance(idx, int) and 0 <= idx < len(locations):
		return locations[idx]
	return None


def _whole(value):
	"""Round a numeric value to a whole number (no decimals). Returns None on failure."""
	try:
		return int(round(float(value)))
	except (TypeError, ValueError):
		return None


def _clockTime(timestamp):
	"""Turn an ISO timestamp like 2026-05-26T05:42 into 05:42."""
	if isinstance(timestamp, str) and len(timestamp) >= 16:
		return timestamp[11:16]
	return timestamp


def geocodeSearch(query):
	"""Search Open-Meteo geocoding for a place name. Returns a list of location dicts."""
	try:
		url = GEOCODE_URL.format(name=urllib.parse.quote(query))
		req = urllib.request.Request(url, headers={"User-Agent": "NVDA-WeatherReport/1.2"})
		response = urllib.request.urlopen(req, timeout=10)
		data = json.loads(response.read().decode("utf-8"))
	except Exception:
		return []
	results = []
	for r in data.get("results", []) or []:
		name = r.get("name", "")
		parts = [p for p in (name, r.get("admin1"), r.get("country")) if p]
		results.append({
			"name": name,
			"label": ", ".join(parts) if parts else name,
			"latitude": r.get("latitude"),
			"longitude": r.get("longitude"),
		})
	return results


class SearchLocationDialog(wx.Dialog):
	"""Search a place by name and pick a result to add."""

	def __init__(self, parent):
		super().__init__(parent, title="Search for a location")
		self.selected = None
		self._results = []
		panel = wx.Panel(self)
		sizer = wx.BoxSizer(wx.VERTICAL)

		sizer.Add(wx.StaticText(panel, label="Place name:"), 0, wx.ALL, 5)
		self.queryCtrl = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
		sizer.Add(self.queryCtrl, 0, wx.EXPAND | wx.ALL, 5)

		searchBtn = wx.Button(panel, label="&Search")
		sizer.Add(searchBtn, 0, wx.ALL, 5)

		sizer.Add(wx.StaticText(panel, label="Results:"), 0, wx.ALL, 5)
		self.resultsList = wx.ListBox(panel, size=(-1, 140), style=wx.LB_SINGLE)
		sizer.Add(self.resultsList, 1, wx.EXPAND | wx.ALL, 5)

		btnSizer = wx.BoxSizer(wx.HORIZONTAL)
		okBtn = wx.Button(panel, wx.ID_OK, "OK")
		cancelBtn = wx.Button(panel, wx.ID_CANCEL, "Cancel")
		btnSizer.Add(okBtn, 0, wx.ALL, 5)
		btnSizer.Add(cancelBtn, 0, wx.ALL, 5)
		sizer.Add(btnSizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)

		searchBtn.Bind(wx.EVT_BUTTON, self._onSearch)
		self.queryCtrl.Bind(wx.EVT_TEXT_ENTER, self._onSearch)
		self.resultsList.Bind(wx.EVT_LISTBOX_DCLICK, self._onOk)
		okBtn.Bind(wx.EVT_BUTTON, self._onOk)

		panel.SetSizer(sizer)
		sizer.Fit(panel)
		self.Fit()
		self.queryCtrl.SetFocus()

	def _onSearch(self, evt):
		query = self.queryCtrl.GetValue().strip()
		if not query:
			return
		self.resultsList.Set(["Searching..."])
		self.resultsList.Enable(False)
		thread = threading.Thread(target=self._doSearch, args=(query,))
		thread.daemon = True
		thread.start()

	def _doSearch(self, query):
		results = geocodeSearch(query)
		wx.CallAfter(self._showResults, results)

	def _showResults(self, results):
		self.resultsList.Enable(True)
		if not results:
			self._results = []
			self.resultsList.Set(["No places found."])
			ui.message("No places found.")
			return
		self._results = results
		self.resultsList.Set([r["label"] for r in results])
		self.resultsList.SetSelection(0)
		self.resultsList.SetFocus()

	def _onOk(self, evt):
		sel = self.resultsList.GetSelection()
		if 0 <= sel < len(self._results):
			self.selected = self._results[sel]
			self.EndModal(wx.ID_OK)
		else:
			ui.message("Please search and select a place first.")


class ManualLocationDialog(wx.Dialog):
	"""Add a location by typing its name and coordinates."""

	def __init__(self, parent):
		super().__init__(parent, title="Add location manually")
		self.location = None
		panel = wx.Panel(self)
		sizer = wx.BoxSizer(wx.VERTICAL)

		sizer.Add(wx.StaticText(panel, label="City name:"), 0, wx.ALL, 5)
		self.cityCtrl = wx.TextCtrl(panel)
		sizer.Add(self.cityCtrl, 0, wx.EXPAND | wx.ALL, 5)

		sizer.Add(wx.StaticText(panel, label="Latitude:"), 0, wx.ALL, 5)
		self.latCtrl = wx.TextCtrl(panel)
		sizer.Add(self.latCtrl, 0, wx.EXPAND | wx.ALL, 5)

		sizer.Add(wx.StaticText(panel, label="Longitude:"), 0, wx.ALL, 5)
		self.lonCtrl = wx.TextCtrl(panel)
		sizer.Add(self.lonCtrl, 0, wx.EXPAND | wx.ALL, 5)

		btnSizer = wx.BoxSizer(wx.HORIZONTAL)
		okBtn = wx.Button(panel, wx.ID_OK, "OK")
		cancelBtn = wx.Button(panel, wx.ID_CANCEL, "Cancel")
		btnSizer.Add(okBtn, 0, wx.ALL, 5)
		btnSizer.Add(cancelBtn, 0, wx.ALL, 5)
		sizer.Add(btnSizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)

		okBtn.Bind(wx.EVT_BUTTON, self._onOk)

		panel.SetSizer(sizer)
		sizer.Fit(panel)
		self.Fit()

	def _onOk(self, evt):
		try:
			lat = float(self.latCtrl.GetValue())
			lon = float(self.lonCtrl.GetValue())
		except ValueError:
			ui.message("Invalid coordinates. Please enter numeric values for latitude and longitude.")
			return
		city = self.cityCtrl.GetValue().strip()
		self.location = {
			"name": city,
			"label": city or f"{lat}, {lon}",
			"latitude": lat,
			"longitude": lon,
		}
		self.EndModal(wx.ID_OK)


class SettingsDialog(wx.Dialog):
	def __init__(self, parent, settings):
		super().__init__(parent, title="Weather Report - Settings")
		# Work on a copy of the locations so Cancel discards changes.
		self._locations = [dict(loc) for loc in settings.get("locations", [])]
		panel = wx.Panel(self)
		sizer = wx.BoxSizer(wx.VERTICAL)

		sizer.Add(wx.StaticText(panel, label="Saved locations (the selected one is used for the weather):"), 0, wx.ALL, 5)
		self.locationsList = wx.ListBox(panel, size=(-1, 120), choices=self._locationLabels(), style=wx.LB_SINGLE)
		idx = settings.get("current_index", 0)
		if isinstance(idx, int) and 0 <= idx < self.locationsList.GetCount():
			self.locationsList.SetSelection(idx)
		elif self.locationsList.GetCount() > 0:
			self.locationsList.SetSelection(0)
		sizer.Add(self.locationsList, 1, wx.EXPAND | wx.ALL, 5)

		btnRow = wx.BoxSizer(wx.HORIZONTAL)
		searchBtn = wx.Button(panel, label="&Search and add...")
		manualBtn = wx.Button(panel, label="Add &manually...")
		removeBtn = wx.Button(panel, label="&Remove")
		btnRow.Add(searchBtn, 0, wx.ALL, 3)
		btnRow.Add(manualBtn, 0, wx.ALL, 3)
		btnRow.Add(removeBtn, 0, wx.ALL, 3)
		sizer.Add(btnRow, 0, wx.ALL, 2)
		searchBtn.Bind(wx.EVT_BUTTON, self._onSearch)
		manualBtn.Bind(wx.EVT_BUTTON, self._onManual)
		removeBtn.Bind(wx.EVT_BUTTON, self._onRemove)

		sizer.Add(wx.StaticText(panel, label="What to announce:"), 0, wx.TOP | wx.LEFT, 10)

		self.fetchingCtrl = wx.CheckBox(panel, label='Say "Fetching weather..." while loading')
		self.fetchingCtrl.SetValue(bool(settings.get("announce_fetching", False)))
		sizer.Add(self.fetchingCtrl, 0, wx.ALL, 5)

		self.feelsLikeCtrl = wx.CheckBox(panel, label="Feels-like temperature")
		self.feelsLikeCtrl.SetValue(bool(settings.get("show_feels_like", True)))
		sizer.Add(self.feelsLikeCtrl, 0, wx.ALL, 5)

		self.humidityCtrl = wx.CheckBox(panel, label="Humidity")
		self.humidityCtrl.SetValue(bool(settings.get("show_humidity", True)))
		sizer.Add(self.humidityCtrl, 0, wx.ALL, 5)

		self.windKmhCtrl = wx.CheckBox(panel, label="Wind in kilometers per hour")
		self.windKmhCtrl.SetValue(bool(settings.get("show_wind_kmh", True)))
		sizer.Add(self.windKmhCtrl, 0, wx.ALL, 5)

		self.windMsCtrl = wx.CheckBox(panel, label="Wind in meters per second")
		self.windMsCtrl.SetValue(bool(settings.get("show_wind_ms", False)))
		sizer.Add(self.windMsCtrl, 0, wx.ALL, 5)

		self.uvCtrl = wx.CheckBox(panel, label="UV index")
		self.uvCtrl.SetValue(bool(settings.get("show_uv_index", False)))
		sizer.Add(self.uvCtrl, 0, wx.ALL, 5)

		self.visibilityCtrl = wx.CheckBox(panel, label="Visibility")
		self.visibilityCtrl.SetValue(bool(settings.get("show_visibility", False)))
		sizer.Add(self.visibilityCtrl, 0, wx.ALL, 5)

		self.sunCtrl = wx.CheckBox(panel, label="Sunrise and sunset")
		self.sunCtrl.SetValue(bool(settings.get("show_sunrise_sunset", False)))
		sizer.Add(self.sunCtrl, 0, wx.ALL, 5)

		btnSizer = wx.BoxSizer(wx.HORIZONTAL)
		okBtn = wx.Button(panel, wx.ID_OK, "OK")
		cancelBtn = wx.Button(panel, wx.ID_CANCEL, "Cancel")
		btnSizer.Add(okBtn, 0, wx.ALL, 5)
		btnSizer.Add(cancelBtn, 0, wx.ALL, 5)
		sizer.Add(btnSizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)

		okBtn.SetDefault()
		panel.SetSizer(sizer)
		sizer.Fit(panel)
		self.Fit()

	def _locationLabels(self):
		labels = []
		for loc in self._locations:
			label = loc.get("label") or loc.get("name") or f"{loc.get('latitude')}, {loc.get('longitude')}"
			labels.append(label)
		return labels

	def _refreshList(self, select):
		self.locationsList.Set(self._locationLabels())
		if self._locations:
			self.locationsList.SetSelection(max(0, min(select, len(self._locations) - 1)))

	def _onSearch(self, evt):
		dlg = SearchLocationDialog(self)
		if dlg.ShowModal() == wx.ID_OK and dlg.selected:
			self._locations.append(dlg.selected)
			self._refreshList(len(self._locations) - 1)
		dlg.Destroy()

	def _onManual(self, evt):
		dlg = ManualLocationDialog(self)
		if dlg.ShowModal() == wx.ID_OK and dlg.location:
			self._locations.append(dlg.location)
			self._refreshList(len(self._locations) - 1)
		dlg.Destroy()

	def _onRemove(self, evt):
		sel = self.locationsList.GetSelection()
		if sel != wx.NOT_FOUND and 0 <= sel < len(self._locations):
			del self._locations[sel]
			self._refreshList(sel)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = "Weather Report"

	def __init__(self):
		super().__init__()
		self._settings = loadSettings()
		self._toolsMenu = gui.mainFrame.sysTrayIcon.toolsMenu
		self._locationMenuItem = self._toolsMenu.Append(
			wx.ID_ANY, "Weather Report - &Settings...", "Manage your locations and choose what the weather report announces"
		)
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self._onLocationMenu, self._locationMenuItem)

	def terminate(self):
		try:
			self._toolsMenu.Remove(self._locationMenuItem)
		except Exception:
			pass

	def _onLocationMenu(self, evt):
		self._showLocationDialog()

	@script(
		description="Announce current weather conditions",
		gesture="kb:NVDA+shift+w",
	)
	def script_announceWeather(self, gesture):
		location = _currentLocation(self._settings)
		if not location:
			ui.message("No location set. Open NVDA Tools menu and choose Weather Report - Settings, or press NVDA+Shift+Control+W.")
			return
		if self._settings.get("announce_fetching", False):
			city = location.get("name", "")
			ui.message(f"Fetching weather for {city}, please wait..." if city else "Fetching weather, please wait...")
		thread = threading.Thread(target=self._fetchWeather)
		thread.daemon = True
		thread.start()

	@script(
		description="Switch to the next saved location",
		gesture="kb:NVDA+shift+control+l",
	)
	def script_nextLocation(self, gesture):
		locations = self._settings.get("locations", [])
		if not locations:
			ui.message("No locations saved. Open Weather Report settings to add one.")
			return
		if len(locations) == 1:
			ui.message(f"Only one location: {locations[0].get('name') or locations[0].get('label')}")
			return
		idx = (self._settings.get("current_index", 0) + 1) % len(locations)
		self._settings["current_index"] = idx
		self._syncLegacyKeys()
		saveSettings(self._settings)
		current = locations[idx]
		ui.message(f"Weather location: {current.get('label') or current.get('name')}")

	@script(
		description="Open Weather Report settings",
		gesture="kb:NVDA+shift+control+w",
	)
	def script_setLocation(self, gesture):
		wx.CallAfter(self._showLocationDialog)

	def _syncLegacyKeys(self):
		"""Keep the old single-location keys in step with the active location."""
		current = _currentLocation(self._settings)
		if current:
			self._settings["latitude"] = current.get("latitude")
			self._settings["longitude"] = current.get("longitude")
			self._settings["city"] = current.get("name", "")

	def _showLocationDialog(self):
		dlg = SettingsDialog(gui.mainFrame, self._settings)
		gui.mainFrame.prePopup()
		result = dlg.ShowModal()
		gui.mainFrame.postPopup()
		if result == wx.ID_OK:
			self._settings["locations"] = dlg._locations
			sel = dlg.locationsList.GetSelection()
			self._settings["current_index"] = sel if sel != wx.NOT_FOUND else 0
			self._settings["announce_fetching"] = dlg.fetchingCtrl.GetValue()
			self._settings["show_feels_like"] = dlg.feelsLikeCtrl.GetValue()
			self._settings["show_humidity"] = dlg.humidityCtrl.GetValue()
			self._settings["show_wind_kmh"] = dlg.windKmhCtrl.GetValue()
			self._settings["show_wind_ms"] = dlg.windMsCtrl.GetValue()
			self._settings["show_uv_index"] = dlg.uvCtrl.GetValue()
			self._settings["show_visibility"] = dlg.visibilityCtrl.GetValue()
			self._settings["show_sunrise_sunset"] = dlg.sunCtrl.GetValue()
			self._syncLegacyKeys()
			saveSettings(self._settings)
			current = _currentLocation(self._settings)
			if current:
				name = current.get("name") or current.get("label")
				ui.message(f"Weather location: {name}")
			else:
				ui.message("No location selected.")
		dlg.Destroy()

	def _hourlyNow(self, data, current):
		"""Return the hourly array index that matches the current hour, or None."""
		hourly = data.get("hourly", {})
		times = hourly.get("time", [])
		currentHour = str(current.get("time", ""))[:13]
		for i, t in enumerate(times):
			if str(t)[:13] == currentHour:
				return i
		return 0 if times else None

	def _fetchWeather(self):
		try:
			location = _currentLocation(self._settings)
			lat = location["latitude"]
			lon = location["longitude"]
			url = API_URL.format(lat=lat, lon=lon)
			req = urllib.request.Request(url, headers={"User-Agent": "NVDA-WeatherReport/1.2"})
			response = urllib.request.urlopen(req, timeout=10)
			data = json.loads(response.read().decode("utf-8"))
			current = data["current"]

			temp = _whole(current.get("temperature_2m"))
			code = current.get("weather_code", -1)
			condition = WMO_CODES.get(code, "Unknown")
			is_day = "Day" if current.get("is_day", 1) == 1 else "Night"

			parts = [condition, f"{temp} degrees Celsius"]

			if self._settings.get("show_feels_like", True):
				feels = _whole(current.get("apparent_temperature"))
				if feels is not None:
					parts.append(f"feels like {feels}")

			windRaw = current.get("wind_speed_10m")
			if self._settings.get("show_wind_kmh", True):
				windKmh = _whole(windRaw)
				if windKmh is not None:
					parts.append(f"wind {windKmh} kilometers per hour")
			if self._settings.get("show_wind_ms", False):
				windMs = _whole(windRaw / 3.6) if isinstance(windRaw, (int, float)) else None
				if windMs is not None:
					parts.append(f"wind {windMs} meters per second")

			if self._settings.get("show_humidity", True):
				humidity = _whole(current.get("relative_humidity_2m"))
				if humidity is not None:
					parts.append(f"humidity {humidity} percent")

			if self._settings.get("show_uv_index", False) or self._settings.get("show_visibility", False):
				idx = self._hourlyNow(data, current)
				hourly = data.get("hourly", {})
				if idx is not None:
					if self._settings.get("show_uv_index", False):
						uvList = hourly.get("uv_index", [])
						if idx < len(uvList):
							uv = _whole(uvList[idx])
							if uv is not None:
								parts.append(f"UV index {uv}")
					if self._settings.get("show_visibility", False):
						visList = hourly.get("visibility", [])
						if idx < len(visList):
							visMeters = visList[idx]
							visKm = _whole(visMeters / 1000) if isinstance(visMeters, (int, float)) else None
							if visKm is not None:
								parts.append(f"visibility {visKm} kilometers")

			if self._settings.get("show_sunrise_sunset", False):
				daily = data.get("daily", {})
				sunrise = daily.get("sunrise", [])
				sunset = daily.get("sunset", [])
				if sunrise and sunset:
					parts.append(f"sunrise {_clockTime(sunrise[0])}, sunset {_clockTime(sunset[0])}")

			parts.append(is_day)

			city = location.get("name", "")
			prefix = f"{city}: " if city else ""
			message = prefix + ", ".join(parts)
			wx.CallAfter(ui.message, message)
		except Exception as e:
			wx.CallAfter(ui.message, f"Failed to fetch weather: {e}")
