from flask import Flask, request, jsonify
from redis import Redis
import requests
import os
import json

app = Flask(__name__)
cache = Redis(host="redis", port=6379)

API_KEY = os.environ.get("WEATHER_API_KEY")

@app.route("/")
def home():
    return """
    <h1>🌤️ Weather Dashboard</h1>
    <form action="/weather" method="get">
        <input name="city" placeholder="Enter city name" style="font-size:20px">
        <button style="font-size:20px">Get Weather</button>
    </form>
    """

@app.route("/weather")
def weather():
    city = request.args.get("city")
    if not city:
        return "Please provide a city name!", 400

    # Check Redis cache first
    cached = cache.get(city)
    if cached:
        data = json.loads(cached)
        data["source"] = "cache 🚀"
        return jsonify(data)

    # Fetch from API
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

    # Cache for 5 minutes
    cache.set(city, json.dumps(result), ex=300)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
