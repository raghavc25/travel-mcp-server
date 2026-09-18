# Travel Itinerary & Packing Assistant — MCP Server

An MCP (Model Context Protocol) server that gives an LLM client weather-aware
travel planning tools: packing lists, day-by-day itinerary tips, and a
combined trip overview for any city. Built with [FastMCP](https://github.com/jlowin/fastmcp)
and [Open-Meteo](https://open-meteo.com/) for geocoding and forecasts — no
API key required.

## How it works

1. **Geocode** — the destination city name is resolved to latitude/longitude
   via Open-Meteo's geocoding API (first match is used).
2. **Forecast** — a daily forecast (min/max temp, precipitation, wind,
   weather code) is fetched for the requested trip length (1–7 days).
3. **Rules-based recommendations** — the forecast is turned into:
   - a packing list (temperature thresholds, rain chance/volume, wind,
     day/night temperature swing all add relevant items)
   - itinerary tips per day (outdoor-friendly vs. rain backup plans, windy
     day warnings)

No LLM call is made inside the server itself — it's a data + heuristics tool
that an MCP client (e.g. Claude) calls and then reasons over.

## Tools exposed

| Tool | Description | Args |
|---|---|---|
| `get_packing_list` | Weather-aware packing list for a trip | `city: str`, `days: int = 3` |
| `get_itinerary_tips` | Day-by-day weather-based planning tips | `city: str`, `days: int = 3` |
| `get_trip_overview` | Packing list + itinerary tips combined | `city: str`, `days: int = 3` |

`days` is clamped to the range 1–7. `city` is a free-text city name, e.g.
`"Goa"` or `"Manali"`.

### Example output

```
$ get_packing_list("Manali", 3)
Packing list for Manali, India (3 days):
  - light jacket or sweater
  - passport/ID
  - phone charger
  - reusable water bottle
  - umbrella
  - waterproof footwear
```

## Requirements

- Python 3.10+
- Dependencies in `requirements.txt`:
  - `mcp[cli]`
  - `httpx`

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running

The server runs over the `streamable-http` transport, bound to `0.0.0.0:8003`:

```bash
python main.py
```

### Connecting an MCP client

Point an MCP client at the streamable-HTTP endpoint, e.g. in a client config:

```json
{
  "mcpServers": {
    "travel-assistant": {
      "url": "http://<host>:8003/mcp"
    }
  }
}
```

## Notes

- Open-Meteo requires no API key and has generous free-tier rate limits,
  suitable for personal/demo use.
- Weather codes are mapped from the [WMO code table](https://open-meteo.com/en/docs)
  to human-readable conditions (clear, overcast, rain, thunderstorm, etc.).
- This is a demo/personal project, not hardened for production traffic
  (no auth, no rate limiting, no input sanitization beyond clamping `days`).
