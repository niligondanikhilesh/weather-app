from flask import Flask, request, jsonify
from redis import Redis
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import requests
import os
import json
import time

app = Flask(__name__)
cache = Redis(host="redis", port=6379)
API_KEY = os.environ.get("WEATHER_API_KEY")

# Prometheus metrics
REQUEST_COUNT = Counter('weather_requests_total', 'Total requests', ['endpoint'])
CACHE_HITS = Counter('weather_cache_hits_total', 'Cache hits')
CACHE_MISSES = Counter('weather_cache_misses_total', 'Cache misses')
REQUEST_LATENCY = Histogram('weather_request_latency_seconds', 'Request latency')

@app.route("/")
def home():
    REQUEST_COUNT.labels(endpoint='/').inc()
    return """
    <h1>🌤️ Weather Dashboard V2</h1>
    <form action="/weather" method="get">
        <input name="city" placeholder="Enter city name" style="font-size:20px">
        <button style="font-size:20px">Get Weather</button>
    </form>
    """

@app.route("/weather")
def weather():
    start = time.time()
    REQUEST_COUNT.labels(endpoint='/weather').inc()
    city = request.args.get("city")
    if not city:
        return "Please provide a city name!", 400
    cached = cache.get(city)
    if cached:
        CACHE_HITS.inc()
        data = json.loads(cached)
        data["source"] = "cache 🚀"
        REQUEST_LATENCY.observe(time.time() - start)
        return jsonify(data)
    CACHE_MISSES.inc()
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        return f"City '{city}' not found!", 404
    weather_data = response.json()
    result = {
        "city": city,
        "temperature": weather_data["main"]["temp"],
        "description": weather_data["weather"][0]["description"],
        "humidity": weather_data["main"]["humidity"],
        "source": "API 🌐"
    }
    cache.set(city, json.dumps(result), ex=300)
    REQUEST_LATENCY.observe(time.time() - start)
    return jsonify(result)

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST} 

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

