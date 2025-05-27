import requests
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

# Obtener variables de entorno
api_key = os.getenv("FOOTBALL_API_KEY")
url_base = os.getenv("FOOTBALL_API_URL")

# Validar existencia de variables
if not api_key or not url_base:
    raise ValueError("⚠️ Las variables FOOTBALL_API_KEY o FOOTBALL_API_URL no están definidas.")

# Construcción de headers
headers = {
    "X-Auth-Token": api_key
}

def obtener_ultimos_partidos(limit=5):
    """Consulta y muestra los últimos partidos disponibles."""
    url = f"{url_base}/matches"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Lanza error si la respuesta no es 2xx

        data = response.json()
        matches = data.get("matches", [])

        if matches:
            print("📅 Últimos partidos disponibles:\n")
            for match in matches[:limit]:
                fecha = match["utcDate"][:10]
                home = match["homeTeam"]["name"]
                away = match["awayTeam"]["name"]
                score = match["score"]["fullTime"]
                print(f"🕒 {fecha} - {home} vs {away} → {score['home']}:{score['away']}")
        else:
            print("⚠️ No se encontraron partidos en este momento.")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error al consultar la API: {e}")

# Ejecutar si se corre directamente
if __name__ == "__main__":
    obtener_ultimos_partidos()
