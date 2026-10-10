"""Weather via wttr.in (no key needed)."""
import json
import urllib.parse
import urllib.request

TOOL = {
    "name": "weather",
    "description": "Current weather and 3-day forecast for a city. Without a city, uses the remembered 'city'.",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
}


def run(params, ctx):
    city = params.get("city")
    if not city:
        hit = ctx.memory.recall("city")
        city = hit[0][1] if hit else ""
    url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl"}), timeout=10) as r:
        d = json.load(r)
    c = d["current_condition"][0]
    out = [f"{city or 'Here'}: {c['weatherDesc'][0]['value']}, {c['temp_C']}°C (feels {c['FeelsLikeC']}°C), "
           f"humidity {c['humidity']}%, wind {c['windspeedKmph']} km/h"]
    for day in d.get("weather", [])[:3]:
        out.append(f"{day['date']}: {day['mintempC']}–{day['maxtempC']}°C, {day['hourly'][4]['weatherDesc'][0]['value']}")
    return "\n".join(out)
