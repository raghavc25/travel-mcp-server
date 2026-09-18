
"""
Travel Itinerary & Packing Assistant — MCP Server
Built with FastMCP, using Open-Meteo (geocoding + forecast) for weather-aware
packing lists and day-by-day itinerary tips. No API key required.
"""

from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("travel-assistant", host="0.0.0.0", port=8003)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: "clear sky", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "depositing rime fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    71: "slight snow", 73: "moderate snow", 75: "heavy snow",
    80: "rain showers", 81: "moderate rain showers", 82: "violent rain showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with heavy hail",
}


async def geocode_city(city: str) -> dict[str, Any] | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(GEOCODE_URL, params={"name": city, "count": 1})
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results")
        if not results:
            return None
        r = results[0]
        return {
            "name": r["name"],
            "country": r.get("country", ""),
            "latitude": r["latitude"],
            "longitude": r["longitude"],
        }


async def fetch_forecast(lat: float, lon: float, days: int) -> dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                 "precipitation_probability_max,windspeed_10m_max,weathercode",
        "forecast_days": days,
        "timezone": "auto",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(FORECAST_URL, params=params)
        resp.raise_for_status()
        return resp.json()


def build_day_summaries(forecast: dict[str, Any]) -> list[dict[str, Any]]:
    daily = forecast["daily"]
    days = []
    for i, date in enumerate(daily["time"]):
        days.append({
            "date": date,
            "temp_min": daily["temperature_2m_min"][i],
            "temp_max": daily["temperature_2m_max"][i],
            "precip_mm": daily["precipitation_sum"][i],
            "precip_chance": daily["precipitation_probability_max"][i],
            "wind_max": daily["windspeed_10m_max"][i],
            "condition": WEATHER_CODES.get(daily["weathercode"][i], "unknown"),
        })
    return days


def packing_list_from_days(days: list[dict[str, Any]]) -> list[str]:
    items = {"passport/ID", "phone charger", "reusable water bottle"}
    max_temp = max(d["temp_max"] for d in days)
    min_temp = min(d["temp_min"] for d in days)
    total_precip = sum(d["precip_mm"] for d in days)
    max_precip_chance = max(d["precip_chance"] for d in days)
    max_wind = max(d["wind_max"] for d in days)

    if max_temp >= 30:
        items.update({"light breathable clothing", "sunscreen", "sunglasses", "hat/cap"})
    if min_temp <= 15:
        items.update({"warm jacket", "thermal layer"})
    elif min_temp <= 20:
        items.add("light jacket or sweater")
    if total_precip > 5 or max_precip_chance >= 50:
        items.update({"umbrella", "rain jacket", "waterproof footwear"})
    if max_wind >= 30:
        items.add("windbreaker")
    if max_temp - min_temp >= 8:
        items.add("layered clothing (big day/night temperature swing)")

    return sorted(items)


def itinerary_tips_from_days(days: list[dict[str, Any]]) -> list[str]:
    tips = []
    for d in days:
        note = f"{d['date']}: {d['condition']}, {d['temp_min']:.0f}–{d['temp_max']:.0f}°C"
        if d["precip_chance"] >= 60:
            note += " — high rain chance, plan indoor backup activities"
        elif d["precip_chance"] >= 30:
            note += " — some rain possible, keep a rain layer handy"
        else:
            note += " — good for outdoor plans"
        if d["wind_max"] >= 30:
            note += "; windy, secure loose items"
        tips.append(note)
    return tips


@mcp.tool()
async def get_packing_list(city: str, days: int = 3) -> str:
    """Generate a weather-aware packing list for a trip.

    Args:
        city: Destination city name, e.g. "Goa" or "Manali"
        days: Trip length in days (1-7)
    """
    days = max(1, min(days, 7))
    location = await geocode_city(city)
    if not location:
        return f"Could not find location: {city}"

    forecast = await fetch_forecast(location["latitude"], location["longitude"], days)
    day_summaries = build_day_summaries(forecast)
    packing = packing_list_from_days(day_summaries)

    lines = [f"Packing list for {location['name']}, {location['country']} ({days} days):"]
    lines += [f"  - {item}" for item in packing]
    return "\n".join(lines)


@mcp.tool()
async def get_itinerary_tips(city: str, days: int = 3) -> str:
    """Generate day-by-day weather-based itinerary planning tips for a trip.

    Args:
        city: Destination city name, e.g. "Goa" or "Manali"
        days: Trip length in days (1-7)
    """
    days = max(1, min(days, 7))
    location = await geocode_city(city)
    if not location:
        return f"Could not find location: {city}"

    forecast = await fetch_forecast(location["latitude"], location["longitude"], days)
    day_summaries = build_day_summaries(forecast)
    tips = itinerary_tips_from_days(day_summaries)

    lines = [f"Itinerary tips for {location['name']}, {location['country']}:"]
    lines += [f"  - {t}" for t in tips]
    return "\n".join(lines)


@mcp.tool()
async def get_trip_overview(city: str, days: int = 3) -> str:
    """Combined packing list + itinerary tips for a destination in one call.

    Args:
        city: Destination city name
        days: Trip length in days (1-7)
    """
    days = max(1, min(days, 7))
    location = await geocode_city(city)
    if not location:
        return f"Could not find location: {city}"

    forecast = await fetch_forecast(location["latitude"], location["longitude"], days)
    day_summaries = build_day_summaries(forecast)
    packing = packing_list_from_days(day_summaries)
    tips = itinerary_tips_from_days(day_summaries)

    lines = [f"Trip overview — {location['name']}, {location['country']} ({days} days)", ""]
    lines.append("Packing list:")
    lines += [f"  - {item}" for item in packing]
    lines.append("")
    lines.append("Day-by-day tips:")
    lines += [f"  - {t}" for t in tips]
    return "\n".join(lines)



if __name__ == "__main__":
    mcp.run(transport="streamable-http")
