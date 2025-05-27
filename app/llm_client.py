import os
import requests
from dotenv import load_dotenv

load_dotenv()

LLM_URL = os.getenv("LLM_API_URL")
LLM_MODEL = os.getenv("LLM_MODEL")

def ask_llm(prompt: str, contexto: str = "", temperature=0.7, max_tokens=800):
    """
    Función para consultar el modelo LLM local (LM Studio)
    """
    
    # Crear el prompt completo
    if contexto:
        full_prompt = f"Contexto: {contexto}\n\nPregunta: {prompt}\n\nResponde de forma clara y concisa en español:"
    else:
        full_prompt = f"{prompt}\n\nResponde de forma clara y concisa en español:"
    
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system", 
                "content": "Eres un experto analista de fútbol. Proporciona análisis precisos y predicciones basadas en datos."
            },
            {
                "role": "user", 
                "content": full_prompt
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }

    try:
        print(f"🔗 Conectando a LLM: {LLM_URL}")
        print(f"🤖 Modelo: {LLM_MODEL}")
        
        response = requests.post(
            LLM_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"📡 Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"✅ Respuesta recibida: {len(content)} caracteres")
            return content
        else:
            error_msg = f"Error HTTP {response.status_code}: {response.text}"
            print(f"❌ {error_msg}")
            return f"⚠️ Error del servidor LLM: {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        error_msg = "No se puede conectar al servidor LLM. ¿Está LM Studio ejecutándose?"
        print(f"❌ {error_msg}")
        return f"⚠️ {error_msg}"
    except requests.exceptions.Timeout:
        error_msg = "Timeout al consultar el LLM"
        print(f"❌ {error_msg}")
        return f"⚠️ {error_msg}"
    except Exception as e:
        error_msg = f"Error inesperado: {str(e)}"
        print(f"❌ {error_msg}")
        return f"⚠️ {error_msg}"

# Función de prueba
if __name__ == "__main__":
    print("🧪 Probando conexión con LLM...")
    respuesta = ask_llm("¿Cómo está el fútbol hoy?")
    print(f"🤖 Respuesta: {respuesta}")