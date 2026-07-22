import requests

def get_weather(city, api_key):
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric"
    }
    response = requests.get(base_url, params=params)
    data = response.json()
    name = data['name']
    temperature = data['main']['temp']
    description = data['weather'][0]['description']
    return (f"Weather in {name}: {temperature} C, {description}")
