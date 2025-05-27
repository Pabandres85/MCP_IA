import requests
import os
from dotenv import load_dotenv

load_dotenv()

headers = {
    "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
    "X-RapidAPI-Host": os.getenv("RAPIDAPI_HOST")
}

def obtener_equipos(league_id, season=2024):
    url = f"{os.getenv('RAPIDAPI_URL')}/teams"
    params = {
        "league": league_id,
        "season": season
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        equipos = response.json().get("response", [])
        return {team["team"]["name"]: team["team"]["id"] for team in equipos}, 200
    else:
        print("Error API:", response.status_code, response.text)
        return {}, response.status_code

