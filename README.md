# Weather Report - NVDA Add-on

An NVDA add-on that announces current weather conditions for your location using the [Open-Meteo](https://open-meteo.com/) API. No API key required.

## Features

- Get current weather with a single keyboard shortcut
- Announces: weather condition, temperature, wind speed, and day/night status
- Optional extra details you can toggle: feels-like temperature, humidity, UV index, visibility, and sunrise/sunset times
- All numbers are announced as whole values (no decimals)
- Configurable location (city name, latitude, and longitude)
- Settings are saved and persist across NVDA restarts
- Non-blocking: weather data is fetched in the background

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `NVDA + Shift + W` | Announce current weather |
| `NVDA + Shift + Control + W` | Open settings |

## Installation

1. Download the latest `.nvda-addon` file from the [Releases](../../releases) page.
2. Open the file, and NVDA will prompt you to install it.
3. Restart NVDA when prompted.

## Settings

1. Press `NVDA + Shift + Control + W` to open the settings dialog.
2. Enter your city name (optional, used in the announcement).
3. Enter your latitude and longitude. You can find these on [Google Maps](https://maps.google.com) by right-clicking any location.
4. Under **What to announce**, tick the extra details you want to hear: feels-like temperature, humidity, UV index, visibility, sunrise/sunset. You can also re-enable the "Fetching weather..." loading message (off by default).
5. Press OK to save.

## Example Output

> Riyadh: Partly cloudy, 33 degrees Celsius, feels like 35, wind 12 kilometers per hour, humidity 40 percent, Day

## Weather Conditions

The add-on supports all WMO standard weather codes including clear sky, cloudy, fog, drizzle, rain, freezing rain, snow, rain showers, snow showers, and thunderstorms.

## Requirements

- NVDA 2021.1 or later (tested up to 2026.1)
- Internet connection

## First-Time Setup

You must set your location before using the addon. Either:
- Open NVDA's Tools menu and select **Weather Report - Settings...**, or
- Press `NVDA + Shift + Control + W`

If you press `NVDA + Shift + W` without setting a location, the addon will remind you to do so.

## License

This project is licensed under the GPL v2 - the same license as NVDA.
