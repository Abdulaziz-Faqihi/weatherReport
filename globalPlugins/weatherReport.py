import globalPluginHandler
from scriptHandler import script
import ui
import config
import gui
import urllib.request
import json
import os
import threading
import wx

CONFIG_DIR = os.path.join(config.getUserDefaultConfigPath(), "weatherReport")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

DEFAULT_SETTINGS = {
	"latitude": None,
	"longitude": None,
	"city": "",
	# Announcement preferences
	"announce_fetching": False,
	"show_feels_like": True,
	"show_humidity": True,
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
	return settings


def saveSettings(settings):
	os.makedirs(CONFIG_DIR, exist_ok=True)
	with open(CONFIG_FILE, "w", encoding="utf-8") as f:
		json.dump(settings, f, indent="\t", ensure_ascii=False)


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


class SettingsDialog(wx.Dialog):
	def __init__(self, parent, settings):
		super().__init__(parent, title="Weather Report - Settings", size=(420, 520))
		panel = wx.Panel(self)
		sizer = wx.BoxSizer(wx.VERTICAL)

		sizer.Add(wx.StaticText(panel, label="City name:"), 0, wx.ALL, 5)
		self.cityCtrl = wx.TextCtrl(panel, value=str(settings.get("city", "")))
		sizer.Add(self.cityCtrl, 0, wx.EXPAND | wx.ALL, 5)

		lat = settings.get("latitude")
		lon = settings.get("longitude")
		sizer.Add(wx.StaticText(panel, label="Latitude:"), 0, wx.ALL, 5)
		self.latCtrl = wx.TextCtrl(panel, value="" if lat is None else str(lat))
		sizer.Add(self.latCtrl, 0, wx.EXPAND | wx.ALL, 5)

		sizer.Add(wx.StaticText(panel, label="Longitude:"), 0, wx.ALL, 5)
		self.lonCtrl = wx.TextCtrl(panel, value="" if lon is None else str(lon))
		sizer.Add(self.lonCtrl, 0, wx.EXPAND | wx.ALL, 5)

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


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = "Weather Report"

	def __init__(self):
		super().__init__()
		self._settings = loadSettings()
		self._toolsMenu = gui.mainFrame.sysTrayIcon.toolsMenu
		self._locationMenuItem = self._toolsMenu.Append(
			wx.ID_ANY, "Weather Report - &Settings...", "Set your location and choose what the weather report announces"
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
		if self._settings.get("latitude") is None or self._settings.get("longitude") is None:
			ui.message("No location set. Open NVDA Tools menu and choose Weather Report - Settings, or press NVDA+Shift+Control+W.")
			return
		if self._settings.get("announce_fetching", False):
			city = self._settings.get("city", "")
			ui.message(f"Fetching weather for {city}, please wait..." if city else "Fetching weather, please wait...")
		thread = threading.Thread(target=self._fetchWeather)
		thread.daemon = True
		thread.start()

	@script(
		description="Open Weather Report settings",
		gesture="kb:NVDA+shift+control+w",
	)
	def script_setLocation(self, gesture):
		wx.CallAfter(self._showLocationDialog)

	def _showLocationDialog(self):
		dlg = SettingsDialog(gui.mainFrame, self._settings)
		gui.mainFrame.prePopup()
		result = dlg.ShowModal()
		gui.mainFrame.postPopup()
		if result == wx.ID_OK:
			try:
				lat = float(dlg.latCtrl.GetValue())
				lon = float(dlg.lonCtrl.GetValue())
			except ValueError:
				ui.message("Invalid coordinates. Please enter numeric values for latitude and longitude.")
				dlg.Destroy()
				return
			self._settings["latitude"] = lat
			self._settings["longitude"] = lon
			self._settings["city"] = dlg.cityCtrl.GetValue().strip()
			self._settings["announce_fetching"] = dlg.fetchingCtrl.GetValue()
			self._settings["show_feels_like"] = dlg.feelsLikeCtrl.GetValue()
			self._settings["show_humidity"] = dlg.humidityCtrl.GetValue()
			self._settings["show_uv_index"] = dlg.uvCtrl.GetValue()
			self._settings["show_visibility"] = dlg.visibilityCtrl.GetValue()
			self._settings["show_sunrise_sunset"] = dlg.sunCtrl.GetValue()
			saveSettings(self._settings)
			city = self._settings["city"]
			ui.message(f"Location set to {city} ({lat}, {lon})" if city else f"Location set to ({lat}, {lon})")
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
			lat = self._settings["latitude"]
			lon = self._settings["longitude"]
			url = API_URL.format(lat=lat, lon=lon)
			req = urllib.request.Request(url, headers={"User-Agent": "NVDA-WeatherReport/1.1"})
			response = urllib.request.urlopen(req, timeout=10)
			data = json.loads(response.read().decode("utf-8"))
			current = data["current"]

			temp = _whole(current.get("temperature_2m"))
			windspeed = _whole(current.get("wind_speed_10m"))
			code = current.get("weather_code", -1)
			condition = WMO_CODES.get(code, "Unknown")
			is_day = "Day" if current.get("is_day", 1) == 1 else "Night"

			parts = [condition, f"{temp} degrees Celsius"]

			if self._settings.get("show_feels_like", True):
				feels = _whole(current.get("apparent_temperature"))
				if feels is not None:
					parts.append(f"feels like {feels}")

			parts.append(f"wind {windspeed} kilometers per hour")

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

			city = self._settings.get("city", "")
			prefix = f"{city}: " if city else ""
			message = prefix + ", ".join(parts)
			wx.CallAfter(ui.message, message)
		except Exception as e:
			wx.CallAfter(ui.message, f"Failed to fetch weather: {e}")
