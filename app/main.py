import base64

from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from geopy.geocoders import Nominatim
import requests
from typing import List
from pydantic import BaseModel
from collections import defaultdict

from schemas import SearchHistory

app = FastAPI(
    title="Weather for users",
    description="This is a combined API documentation for all microservices.",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

API_URL = "https://api.open-meteo.com/v1/forecast"
API_PARAMS = {
    "hourly": "temperature_2m",
    "daily": "temperature_2m_max,temperature_2m_min",
    "timezone": "auto"
}

search_history = defaultdict(int)


def get_weather(city: str):
    geolocator = Nominatim(user_agent="weather_app")
    location = geolocator.geocode(city)

    if location:
        lat, lon = location.latitude, location.longitude
        weather_response = requests.get(API_URL, params={**API_PARAMS, "latitude": lat, "longitude": lon})
        weather_data = weather_response.json()
        return weather_data
    return None


@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    recent_city = request.cookies.get("recent_city")
    if recent_city:
        recent_city = base64.b64decode(recent_city.encode()).decode()
    return templates.TemplateResponse("form.html", {"request": request, "recent_city": recent_city})


@app.post("/", response_class=HTMLResponse)
async def handle_form(request: Request, response: Response, city: str = Form(...)):
    weather_data = get_weather(city)
    if weather_data:
        search_history[city] += 1
        encoded_city = base64.b64encode(city.encode()).decode()
        response.set_cookie(key='recent_city', value=encoded_city)
    return templates.TemplateResponse("result.html", {"request": request, "weather_data": weather_data, "city": city})


@app.get("/api/history", response_model=List[SearchHistory])
async def get_history():
    return [SearchHistory(city=city, count=count) for city, count in search_history.items()]


@app.get("/autocomplete/{query}", response_model=List[str])
async def autocomplete(query: str):
    geolocator = Nominatim(user_agent="weather_app")
    locations = geolocator.geocode(query, exactly_one=False, limit=5)
    if locations:
        return [location.address for location in locations]
    return []



