# Weather Report - NVDA Add-on

An NVDA add-on that announces current weather conditions for your location using the [Open-Meteo](https://open-meteo.com/) API. No API key required.

## Features

- Get current weather with a single keyboard shortcut
- Announces: weather condition, temperature, wind speed, and day/night status
- Configurable location (city name, latitude, and longitude)
- Settings are saved and persist across NVDA restarts
- Non-blocking: weather data is fetched in the background

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `NVDA + Shift + W` | Announce current weather |
| `NVDA + Shift + Control + W` | Set your location |

## Installation

1. Download the latest `.nvda-addon` file from the [Releases](../../releases) page.
2. Open the file, and NVDA will prompt you to install it.
3. Restart NVDA when prompted.

## Setting Your Location

1. Press `NVDA + Shift + Control + W` to open the location dialog.
2. Enter your city name (optional, used in the announcement).
3. Enter your latitude and longitude. You can find these on [Google Maps](https://maps.google.com) by right-clicking any location.
4. Press OK to save.

## Example Output

> Jazan: Partly cloudy, 32.5 degrees Celsius, Wind 12.3 kilometers per hour, Day

## Weather Conditions

The add-on supports all WMO standard weather codes including clear sky, cloudy, fog, drizzle, rain, freezing rain, snow, rain showers, snow showers, and thunderstorms.

## Requirements

- NVDA 2021.1 or later
- Internet connection

## License

This project is licensed under the GPL v2 - the same license as NVDA.
