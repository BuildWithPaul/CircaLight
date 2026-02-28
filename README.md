# Govee Solar Flux Controller 🌅💡

Automatically adjusts your Govee smart light's brightness and color temperature based on sunset/sunrise, creating natural circadian lighting.

<img width="1189" height="587" alt="Screenshot 2026-02-28 at 11 18 52" src="https://github.com/user-attachments/assets/4625b375-d4f8-4de9-86f2-a65dfa94d555" />

## Features

- 🌍 Location-aware sunrise/sunset calculations
- 📊 Visual graph of 24-hour light cycles
- 🔌 Real-time Govee API control
- 🎯 Smooth transitions throughout the day

## Setup

1. **Install dependencies:**
   ```bash
   pip install requests suntime
   ```

2. **Get your API key** from [Govee API Portal](https://openapi.api.govee.com)

3. **Update the script:**
   ```python
   GOVEE_API_KEY = "your-key-here"
   DEVICE_ID = "your-device-id"
   LATITUDE = 45.566
   LONGITUDE = 5.445
   TIMEZONE = "Europe/Paris"
   ```

## Usage

```bash
python goove.py
```

Shows a daily graph and adjusts your light. Schedule with cron:
```bash
*/30 * * * * python /Users/user/goove.py
```

## Daily Cycle

| Time | Effect |
|------|--------|
| Night | 5% brightness, 2200K (warm) |
| Pre-sunrise | Gradual warm-up |
| Day | 100% brightness, 6500K (cool) |
| Sunset | Gradual cool-down |

## Configuration

Edit these in the script:
- `BRIGHT_MIN/MAX` - Brightness range (1-100)
- `TEMP_MIN/MAX` - Color range in Kelvin
- `wake_offset` - Minutes before sunrise to start
- `sleep_offset` - Minutes after sunset to finish

## Troubleshooting

**Exit 127:** Use `python3 goove.py` or check your PATH  
**Light not responding:** Verify API key and device ID in Govee app  
**No graph:** Add `plt.savefig('flux.png')` if no display available

---

Graph shows brightness and temperature throughout the day. Customize for your location and preferences!
