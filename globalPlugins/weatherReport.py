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
	"latitude": 17.15,
	"longitude": 42.72,
	"city": "Jazan",
}

API_URL = "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"

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
	if os.path.isfile(CONFIG_FILE):
		try:
			with open(CONFIG_FILE, "r", encoding="utf-8") as f:
				return json.load(f)
		except Exception:
			pass
	return dict(DEFAULT_SETTINGS)


def saveSettings(settings):
	os.makedirs(CONFIG_DIR, exist_ok=True)
	with open(CONFIG_FILE, "w", encoding="utf-8") as f:
		json.dump(settings, f, indent="\t", ensure_ascii=False)


class LocationDialog(wx.Dialog):
	def __init__(self, parent, settings):
		super().__init__(parent, title="Weather Report - Set Location", size=(400, 250))
		panel = wx.Panel(self)
		sizer = wx.BoxSizer(wx.VERTICAL)

		sizer.Add(wx.StaticText(panel, label="City name:"), 0, wx.ALL, 5)
		self.cityCtrl = wx.TextCtrl(panel, value=str(settings.get("city", "")))
		sizer.Add(self.cityCtrl, 0, wx.EXPAND | wx.ALL, 5)

		sizer.Add(wx.StaticText(panel, label="Latitude:"), 0, wx.ALL, 5)
		self.latCtrl = wx.TextCtrl(panel, value=str(settings.get("latitude", "")))
		sizer.Add(self.latCtrl, 0, wx.EXPAND | wx.ALL, 5)

		sizer.Add(wx.StaticText(panel, label="Longitude:"), 0, wx.ALL, 5)
		self.lonCtrl = wx.TextCtrl(panel, value=str(settings.get("longitude", "")))
		sizer.Add(self.lonCtrl, 0, wx.EXPAND | wx.ALL, 5)

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

	@script(
		description="Announce current weather conditions",
		gesture="kb:NVDA+shift+w",
	)
	def script_announceWeather(self, gesture):
		city = self._settings.get("city", "")
		ui.message(f"Fetching weather for {city}, please wait..." if city else "Fetching weather, please wait...")
		thread = threading.Thread(target=self._fetchWeather)
		thread.daemon = True
		thread.start()

	@script(
		description="Set weather location",
		gesture="kb:NVDA+shift+control+w",
	)
	def script_setLocation(self, gesture):
		wx.CallAfter(self._showLocationDialog)

	def _showLocationDialog(self):
		dlg = LocationDialog(gui.mainFrame, self._settings)
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
			saveSettings(self._settings)
			city = self._settings["city"]
			ui.message(f"Location set to {city} ({lat}, {lon})" if city else f"Location set to ({lat}, {lon})")
		dlg.Destroy()

	def _fetchWeather(self):
		try:
			lat = self._settings["latitude"]
			lon = self._settings["longitude"]
			url = API_URL.format(lat=lat, lon=lon)
			req = urllib.request.Request(url, headers={"User-Agent": "NVDA-WeatherReport/1.0"})
			response = urllib.request.urlopen(req, timeout=10)
			data = json.loads(response.read().decode("utf-8"))
			weather = data["current_weather"]
			temp = weather["temperature"]
			windspeed = weather["windspeed"]
			code = weather.get("weathercode", -1)
			condition = WMO_CODES.get(code, "Unknown")
			is_day = "Day" if weather.get("is_day", 1) == 1 else "Night"
			city = self._settings.get("city", "")
			prefix = f"{city}: " if city else ""
			message = (
				f"{prefix}{condition}, {temp} degrees Celsius, "
				f"Wind {windspeed} kilometers per hour, {is_day}"
			)
			wx.CallAfter(ui.message, message)
		except Exception as e:
			wx.CallAfter(ui.message, f"Failed to fetch weather: {e}")
