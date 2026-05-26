# Weather Report - NVDA Add-on

An NVDA add-on that announces current weather conditions for your location using the [Open-Meteo](https://open-meteo.com/) API. No API key required.

## Features

- Get current weather with a single keyboard shortcut
- Announces: weather condition, temperature, wind speed, and day/night status
- Search for a place by name instead of typing coordinates
- Save multiple locations and switch between them with a shortcut
- Optional extra details you can toggle: feels-like temperature, humidity, wind in km/h and/or m/s, UV index, visibility, and sunrise/sunset times
- All numbers are announced as whole values (no decimals)
- Settings are saved and persist across NVDA restarts
- Non-blocking: weather data is fetched in the background

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `NVDA + Shift + W` | Announce current weather |
| `NVDA + Shift + Control + L` | Switch to the next saved location |
| `NVDA + Shift + Control + W` | Open settings |

## Installation

1. Download the latest `.nvda-addon` file from the [Releases](../../releases) page.
2. Open the file, and NVDA will prompt you to install it.
3. Restart NVDA when prompted.

## Settings

1. Press `NVDA + Shift + Control + W` to open the settings dialog.
2. Under **Saved locations**, add the places you want:
   - **Search and add...** — type a place name (e.g. "Riyadh"), search, and pick a result from the list. Coordinates are filled in for you.
   - **Add manually...** — type a city name plus latitude and longitude yourself. You can find coordinates on [Google Maps](https://maps.google.com) by right-clicking any location.
   - **Remove** — delete the selected location.
3. The location highlighted in the list is the one used for the weather. You can also cycle between saved locations any time with `NVDA + Shift + Control + L`.
4. Under **What to announce**, tick the extra details you want to hear: feels-like temperature, humidity, wind in kilometers per hour, wind in meters per second, UV index, visibility, sunrise/sunset. You can also re-enable the "Fetching weather..." loading message (off by default).
5. Press OK to save.

## Example Output

> Riyadh: Partly cloudy, 33 degrees Celsius, feels like 35, wind 12 kilometers per hour, humidity 40 percent, Day

## Weather Conditions

The add-on supports all WMO standard weather codes including clear sky, cloudy, fog, drizzle, rain, freezing rain, snow, rain showers, snow showers, and thunderstorms.

## Requirements

- NVDA 2021.1 or later (tested up to 2026.1)
- Internet connection

## First-Time Setup

You must add at least one location before using the addon. Either:
- Open NVDA's Tools menu and select **Weather Report - Settings...**, or
- Press `NVDA + Shift + Control + W`

Then use **Search and add...** to find your city by name, or **Add manually...** to type coordinates. If you press `NVDA + Shift + W` without any saved location, the addon will remind you to add one.

## License

This project is licensed under the GPL v2 - the same license as NVDA.
