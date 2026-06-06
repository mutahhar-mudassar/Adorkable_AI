"""
Adorkable AI Weather API Client

OpenWeatherMap API integration for live weather data and forecasts.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import requests

from backend.config import OPENWEATHER_API_KEY


# =============================================================================
# Constants
# =============================================================================

BASE_URL = "https://api.openweathermap.org/data/2.5"
FORECAST_URL = f"{BASE_URL}/forecast"
CURRENT_URL = f"{BASE_URL}/weather"

# Default fallback values
DEFAULT_WEATHER = {
    "temp_c": 22.0,
    "condition": "Clear",
    "humidity": 50,
    "description": "Default fallback",
    "wind_speed": 5.0,
    "city": "Unknown"
}


# =============================================================================
# Current Weather
# =============================================================================

def get_current_weather(city: str) -> Dict:
    """
    Get current weather for a city.
    
    Args:
        city: City name (e.g., "London", "New York", "Tokyo")
        
    Returns:
        Dictionary with weather data:
        {
            "temp_c": float,        # Temperature in Celsius
            "condition": str,       # Main condition (Clear, Clouds, Rain, etc.)
            "humidity": int,        # Humidity percentage
            "description": str,     # Detailed description
            "wind_speed": float,    # Wind speed in m/s
            "city": str             # City name
        }
        
        Returns DEFAULT_WEATHER if API call fails.
        
    Example:
        >>> weather = get_current_weather("London")
        >>> print(f"It's {weather['temp_c']}°C and {weather['description']}")
        It's 15.5°C and scattered clouds
    """
    if not OPENWEATHER_API_KEY:
        print("⚠️ No OpenWeather API key configured, using default")
        return DEFAULT_WEATHER
    
    try:
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"  # Celsius
        }
        
        response = requests.get(CURRENT_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check for API errors
        if data.get("cod") not in [200, "200"]:
            print(f"⚠️ Weather API error: {data.get('message', 'Unknown error')}")
            return DEFAULT_WEATHER
        
        # Parse response
        weather = {
            "temp_c": float(data["main"]["temp"]),
            "condition": data["weather"][0]["main"],
            "humidity": int(data["main"]["humidity"]),
            "description": data["weather"][0]["description"],
            "wind_speed": float(data.get("wind", {}).get("speed", 0)),
            "city": data.get("name", city)
        }
        
        return weather
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Weather API request failed: {e}")
        return DEFAULT_WEATHER
    except (KeyError, ValueError) as e:
        print(f"⚠️ Error parsing weather data: {e}")
        return DEFAULT_WEATHER


# =============================================================================
# Forecast
# =============================================================================

def get_7day_forecast(city: str) -> List[Dict]:
    """
    Get 7-day weather forecast for a city.
    
    Uses the 5-day/3-hour forecast API and aggregates into daily forecasts.
    
    Args:
        city: City name
        
    Returns:
        List of daily forecasts:
        [
            {
                "date": str,        # ISO date string
                "temp_c": float,    # Average temperature
                "temp_min": float,  # Min temperature
                "temp_max": float,  # Max temperature
                "condition": str,   # Main condition
                "description": str, # Description
                "humidity": int,    # Average humidity
                "icon": str         # Weather icon code
            },
            ...
        ]
        
    Returns fallback data if API call fails.
    """
    if not OPENWEATHER_API_KEY:
        print("⚠️ No OpenWeather API key configured, using default forecast")
        return _generate_default_forecast()
    
    try:
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "cnt": 40  # Maximum 3-hour intervals (5 days * 8 intervals/day = 40)
        }
        
        response = requests.get(FORECAST_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("cod") not in [200, "200"]:
            print(f"⚠️ Forecast API error: {data.get('message', 'Unknown error')}")
            return _generate_default_forecast()
        
        # Aggregate 3-hour intervals into daily forecasts
        daily_data = {}
        
        for item in data.get("list", []):
            # Parse date
            dt_txt = item.get("dt_txt", "")
            date_str = dt_txt.split(" ")[0] if dt_txt else ""
            
            if not date_str:
                continue
            
            if date_str not in daily_data:
                daily_data[date_str] = {
                    "temps": [],
                    "temps_min": [],
                    "temps_max": [],
                    "humidities": [],
                    "conditions": [],
                    "descriptions": [],
                    "icons": []
                }
            
            day = daily_data[date_str]
            day["temps"].append(item["main"]["temp"])
            day["temps_min"].append(item["main"].get("temp_min", item["main"]["temp"]))
            day["temps_max"].append(item["main"].get("temp_max", item["main"]["temp"]))
            day["humidities"].append(item["main"]["humidity"])
            
            if item.get("weather"):
                day["conditions"].append(item["weather"][0]["main"])
                day["descriptions"].append(item["weather"][0]["description"])
                day["icons"].append(item["weather"][0].get("icon", ""))
        
        # Process into final forecast
        forecast = []
        for date_str in sorted(daily_data.keys())[:7]:  # Limit to 7 days
            day = daily_data[date_str]
            
            # Get most common condition
            from collections import Counter
            condition_counter = Counter(day["conditions"])
            main_condition = condition_counter.most_common(1)[0][0]
            
            # Get most common description
            desc_counter = Counter(day["descriptions"])
            main_description = desc_counter.most_common(1)[0][0]
            
            forecast.append({
                "date": date_str,
                "temp_c": round(sum(day["temps"]) / len(day["temps"]), 1),
                "temp_min": round(min(day["temps_min"]), 1),
                "temp_max": round(max(day["temps_max"]), 1),
                "condition": main_condition,
                "description": main_description,
                "humidity": round(sum(day["humidities"]) / len(day["humidities"])),
                "icon": day["icons"][0] if day["icons"] else ""
            })
        
        return forecast
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Forecast API request failed: {e}")
        return _generate_default_forecast()
    except (KeyError, ValueError) as e:
        print(f"⚠️ Error parsing forecast data: {e}")
        return _generate_default_forecast()


def _generate_default_forecast() -> List[Dict]:
    """
    Generate a default 7-day forecast when API is unavailable.
    
    Returns:
        List of default daily forecasts
    """
    today = datetime.now()
    base_temp = DEFAULT_WEATHER["temp_c"]
    
    forecast = []
    for i in range(7):
        date = today + timedelta(days=i)
        # Slight variation in temperature
        temp_variation = (i % 3 - 1) * 3  # -3, 0, +3, repeating
        
        forecast.append({
            "date": date.strftime("%Y-%m-%d"),
            "temp_c": round(base_temp + temp_variation, 1),
            "temp_min": round(base_temp + temp_variation - 5, 1),
            "temp_max": round(base_temp + temp_variation + 5, 1),
            "condition": DEFAULT_WEATHER["condition"],
            "description": DEFAULT_WEATHER["description"],
            "humidity": DEFAULT_WEATHER["humidity"],
            "icon": "01d"
        })
    
    return forecast


# =============================================================================
# Utilities
# =============================================================================

def is_rainy_condition(condition: str) -> bool:
    """
    Check if weather condition involves rain.
    
    Args:
        condition: Weather condition string
        
    Returns:
        True if rainy condition
    """
    rain_conditions = [
        "rain", "drizzle", "thunderstorm", "showers",
        "light rain", "moderate rain", "heavy rain",
        "thunderstorm with rain"
    ]
    return condition.lower() in rain_conditions


def is_cold_weather(temp_c: float) -> bool:
    """
    Check if temperature is cold.
    
    Args:
        temp_c: Temperature in Celsius
        
    Returns:
        True if cold (< 15°C)
    """
    return temp_c < 15


def is_hot_weather(temp_c: float) -> bool:
    """
    Check if temperature is hot.
    
    Args:
        temp_c: Temperature in Celsius
        
    Returns:
        True if hot (> 28°C)
    """
    return temp_c > 28


def get_weather_icon_url(icon_code: str) -> str:
    """
    Get URL for weather icon.
    
    Args:
        icon_code: Icon code from API
        
    Returns:
        URL to icon image
    """
    return f"https://openweathermap.org/img/wn/{icon_code}@2x.png"


def format_weather_description(weather: Dict) -> str:
    """
    Format weather data into human-readable string.
    
    Args:
        weather: Weather dictionary
        
    Returns:
        Formatted description
    """
    temp = weather.get("temp_c", 0)
    desc = weather.get("description", "unknown")
    condition = weather.get("condition", "")
    
    # Create contextual description
    if temp < 10:
        temp_desc = "freezing"
    elif temp < 15:
        temp_desc = "cold"
    elif temp < 22:
        temp_desc = "cool"
    elif temp < 28:
        temp_desc = "warm"
    else:
        temp_desc = "hot"
    
    return f"It's {temp}°C and {desc} — {temp_desc} weather conditions"


# ✅ backend/utils/weather_api.py generated — Adorkable AI
