#!/usr/bin/env python3

import requests
import uuid
from datetime import datetime, timedelta, time as dt_time
from suntime import Sun, SunTimeException  # or Astral, choose one
import pytz

# 🔑 Replace this with your actual Govee API key
GOVEE_API_KEY = "xxxxx"
CONTROL_URL = "https://openapi.api.govee.com/router/api/v1/device/control"

DEVICE_ID = "xxxxx
SKU = "H60A1"

# Color temp & brightness bounds from your lamp capabilities
TEMP_MIN = 2200
TEMP_MAX = 6500

BRIGHT_MIN = 5    # minimal brightness
BRIGHT_MAX = 100   # maximal brightness

# Latitude / Longitude 
LATITUDE = 45.1     # approx
LONGITUDE = 5.1     # approx

# Timezone string for La Tour-du-Pin
TIMEZONE = "Europe/Paris"

# Minimum change thresholds to avoid unnecessary API calls
MIN_DELTA_TEMP = 50
MIN_DELTA_BRIGHT = 0

# Save last sent values somewhere persistent (file) if you want to avoid sending if no significant change
STATE_FILE = "/tmp/govee_flux_state.json"

def compute_flux(now: datetime, sunrise: datetime, sunset: datetime):
    """
    Compute ideal brightness and color temperature based on time of day.
    
    Args:
        now: Current datetime (timezone-aware)
        sunrise: Today's sunrise time (timezone-aware)
        sunset: Today's sunset time (timezone-aware)
    
    Returns:
        tuple: (brightness_percent, color_temp_kelvin)
    """
    print(f"[DEBUG] now: {now}")
    # Convert times to minutes since midnight for easier calculations
    now_minutes = now.hour * 60 + now.minute
    sunrise_minutes = sunrise.hour * 60 + sunrise.minute
    sunset_minutes = sunset.hour * 60 + sunset.minute

    # Define key times of day (in minutes from sunrise/sunset)
    wake_offset = -60  # 1 hour before sunrise
    sleep_offset = 120  # 2 hours after sunset
    
    wake_time = sunrise_minutes + wake_offset
    sleep_time = sunset_minutes + sleep_offset
    
    # Default night values
    brightness = BRIGHT_MIN
    tempK = TEMP_MIN
    
    if now_minutes < wake_time:
        print(f"[DEBUG] Before wake: brightness={brightness}, tempK={tempK}")
        # Before wake: minimum values
        brightness = BRIGHT_MIN
        tempK = TEMP_MIN
    
    elif now_minutes < sunrise_minutes:
        print(f"[DEBUG] Wake to sunrise: temp and brightness increasing")
        # Wake to sunrise: increase both temperature and brightness
        progress = (now_minutes - wake_time) / (sunrise_minutes - wake_time)
        brightness = BRIGHT_MIN + (BRIGHT_MAX - BRIGHT_MIN) * progress
        tempK = TEMP_MIN + (TEMP_MAX - TEMP_MIN) * progress
    
    elif now_minutes < sunset_minutes:
        print(f"[DEBUG] Daytime: brightness and temp following solar curve")
        # Daytime: bright and cool
        # Peak brightness/temp at solar noon
        solar_noon = sunrise_minutes + (sunset_minutes - sunrise_minutes) / 2
        dist_from_noon = abs(now_minutes - solar_noon)
        max_dist = solar_noon - sunrise_minutes
        
        # Set max brightness at sunrise, only decrease after solar_noon
        if now_minutes <= solar_noon:
            brightness = BRIGHT_MAX
            tempK = TEMP_MAX
        else:
            # After solar noon: follow original parabolic curve for both
            day_progress = 1 - (dist_from_noon / max_dist) ** 2
            brightness = 50 + (BRIGHT_MAX - 50) * day_progress
            tempK = TEMP_MAX/2 + (TEMP_MAX - TEMP_MAX/2) * day_progress
    
    elif now_minutes < sleep_time:
        print(f"[DEBUG] Sunset to sleep: brightness and temp decreasing")
        # Sunset to sleep: gradually decrease
        progress = (now_minutes - sunset_minutes) / (sleep_time - sunset_minutes)
        brightness = 50 - (50 - BRIGHT_MIN) * progress
        tempK = TEMP_MAX/2 - (TEMP_MAX/2 - TEMP_MIN) * progress
    
    # Ensure values are within bounds
    brightness = max(BRIGHT_MIN, min(BRIGHT_MAX, round(brightness)))
    tempK = max(TEMP_MIN, min(TEMP_MAX, round(tempK)))
    
    return brightness, tempK

def write_last_state(brightness, tempK):
    """Write last brightness/temp to file."""
    try:
        with open(STATE_FILE, "w") as f:
            import json
            json.dump({"brightness": brightness, "tempK": tempK}, f)
    except Exception as e:
        print("Warning: could not write state file:", e)


def send_control(sku: str, device: str, inst_type: str, inst_name: str, value):
    payload = {
        "requestId": str(uuid.uuid4()),
        "payload": {
            "sku": sku,
            "device": device,
            "capability": {
                "type": inst_type,
                "instance": inst_name,
                "value": value
            }
        }
    }
    headers = {
        "Content-Type": "application/json",
        "Govee-API-Key": GOVEE_API_KEY
    }

    # ✅ Use POST instead of PUT
    resp = requests.post(CONTROL_URL, json=payload, headers=headers)
    print(resp.text)
    if resp.status_code != 200:
        print(f"⚠️ HTTP error: {resp.status_code}: {resp.text}")
        return False

    j = resp.json()
    if j.get("code") != 200:
        print(f"⚠️ Control API error: {j}")
        return False

    print(f"✅ Controlled {inst_name} to {value}")
    return True

def get_sun_times_local(date):
    """Return sunrise and sunset as timezone-aware datetimes in local time."""
    tz_local = pytz.timezone(TIMEZONE)
    sun = Sun(LATITUDE, LONGITUDE)

    try:
        date_dt = datetime.combine(date, datetime.min.time())

        # suntime returns UTC datetimes (tz-aware)
        sr_utc = sun.get_sunrise_time(date_dt)
        ss_utc = sun.get_sunset_time(date_dt)

        # Convert to local timezone
        sr_local = sr_utc.astimezone(tz_local)
        ss_local = ss_utc.astimezone(tz_local)

        # 🔧 If sunset < sunrise (happens when suntime crosses UTC day boundary),
        # recompute sunset for the next UTC day
        if ss_local.date() < sr_local.date():
            next_day = date_dt + timedelta(days=1)
            ss_utc = sun.get_sunset_time(next_day)
            ss_local = ss_utc.astimezone(tz_local)

        print(f"[DEBUG] Sunrise UTC: {sr_utc}, local: {sr_local}")
        print(f"[DEBUG] Sunset UTC: {ss_utc}, local: {ss_local}")

        return sr_local, ss_local

    except SunTimeException as e:
        raise RuntimeError(f"Error computing sun times: {e}")

def main():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)  # current local time (aware)
    sr, ss = get_sun_times_local(now.date())
    
    brightness, tempK = compute_flux(now, sr, ss)

    send_control(SKU, DEVICE_ID, "devices.capabilities.range", "brightness", brightness)
    send_control(SKU, DEVICE_ID, "devices.capabilities.color_setting", "colorTemperatureK", tempK)

if __name__ == "__main__":
    # Check GOVEE_API_KEY is set
    if GOVEE_API_KEY == "YOUR_GOVEE_API_KEY":
        print("Please set your Govee API key in the script!")
    else:
        main()
