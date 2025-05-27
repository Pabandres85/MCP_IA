import requests
import os
from dotenv import load_dotenv

load_dotenv()

headers = {
    "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
    "X-RapidAPI-Host": os.getenv("RAPIDAPI_HOST")
}

def obtener_lesiones(team_id, season=2024):
    url = f"{os.getenv('RAPIDAPI_URL')}/injuries"
    params = {
        "team": team_id,
        "season": season
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        return response.json().get("response", []), 200
    else:
        print("Error API:", response.status_code, response.text)
        return [], response.status_code
