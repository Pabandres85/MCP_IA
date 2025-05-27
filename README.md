# MCP\_IA — Model Context Protocol con IA Local para Fútbol

![MCP\_IA](https://img.shields.io/badge/status-en%20desarrollo-blue)

`MCP_IA` es una plataforma integral que combina un **modelo de lenguaje local (LLM)** alojado en **LM Studio**, una **interfaz interactiva en Streamlit** y un **bot de Telegram**, todo orientado a ofrecer predicciones futbolísticas, análisis detallado de ligas, equipos y partidos, así como reportes descargables.

---

## 🚀 Características Principales

Este sistema implementa el enfoque **Model Context Protocol (MCP)**, una arquitectura que orquesta:

* Contexto estructurado basado en datos deportivos actualizados.
* Prompts especializados y auditados para interacción natural.
* Un modelo LLM local que opera sobre esos contextos y produce respuestas predictivas o explicativas.

La arquitectura MCP garantiza que el modelo reciba:

* **Datos relevantes**, extraídos de APIs externas.

* **Contexto enriquecido**, como análisis previos, resultados recientes o patrones históricos.

* **Plantillas de prompts**, optimizadas para diferentes tipos de consulta (por liga, por equipo, predicción, revisión, etc.).

* ✨ **Dashboard interactivo** con 7 pestañas para visualización de datos, predicciones y métricas.

* 🚀 **IA local** ejecutada desde LM Studio (modelo Mistral 7B Instruct v0.1).

* 📲 **Bot de Telegram** conectado a la misma IA para consultas conversacionales.

* 🔍 Análisis por equipo, predicciones de partidos y estado de jugadores.

* 📊 Exportación de datos en CSV, JSON y PDF.

* ⌛ Métricas de rendimiento y uso del bot.

---

## 🔄 Tecnologías Utilizadas

* **Python 3.10+**
* **Streamlit** para el dashboard
* **LM Studio** para el despliegue de LLM local (vía HTTP)
* **Telegram Bot API** para interacción conversacional
* **Pandas / Plotly** para visualizaciones
* **Docker** y `supervisord` para despliegue

---

## 🔹 Estructura del Proyecto

```
MCP_IA/
├── app/
│   ├── data/                   # Archivos de configuración y JSONs
│   ├── logs/                   # Logs de interacción, rendimiento y sistema
│   ├── pages/                  # Módulos funcionales de la app
│   │   ├── dashboard.py        # Dashboard principal con Streamlit
│   │   ├── telegram_metrics.py # Métricas del bot de Telegram
│   │   ├── generate_pdf.py     # Utilidad para exportar análisis como PDF
│   │   ├── injuries_service.py # Consulta de estado de jugadores (lesiones)
│   │   ├── llm_client.py       # Conector con el modelo LLM local vía HTTP
│   │   ├── logger_service.py   # Registro de interacciones y logs
│   │   ├── teams_service.py    # Servicio para obtener información de equipos
│   │   └── main.py             # Punto de entrada
│   └── telegram_bot.py         # Lógica del bot de Telegram
├── Dockerfile                  # Imagen para despliegue
├── requirements.txt            # Dependencias del entorno
├── supervisord.conf            # Configuración de servicios en segundo plano
├── .gitignore
└── .env.example                # Plantilla de entorno con claves dummy
```

---

## 🔎 Detalles del Dashboard

El archivo principal es [`dashboard.py`](https://github.com/Pabandres85/MCP_IA/blob/master/app/pages/dashboard.py), que cuenta con:

### 1. 🏟️ Partidos

Consulta y visualización de partidos pasados por competición y rango de fechas.

### 2. 📊 Estadísticas Globales

Análisis de goles, empates, probabilidad por equipo y predicción general con IA.

### 3. 🔍 Por equipo

Detalle de rendimiento, goles, y estado de jugadores lesionados usando RapidAPI.

### 4. 🧠 Análisis con IA

Consulta libre al modelo IA sobre el rendimiento y predicciones usando contexto.

### 5. 📅 Exportar

Exporta los datos como CSV o JSON según el periodo y competición seleccionada.

### 6. 🔮 Predicción de Partidos

Análisis por partido futuro entre equipos específicos con comparativos visuales.

### 7. 📱 Métricas Telegram

Muestra actividad del bot: interacciones, uso horario, consultas por liga y rendimiento del sistema.

---

## 🧵 Bot de Telegram Inteligente

El bot de Telegram (archivo `telegram_bot.py`) actúa como un chatbot conversacional que integra:

* 🧠 Respuestas generadas por IA local.
* ⚙️ Prompts configurables desde archivo JSON para cada tipo de pregunta.
* 🔄 Contexto en tiempo real a partir de partidos recientes y futuros.
* 📊 Análisis de equipos y predicciones personalizadas.
* 📁 Cache inteligente y respuesta auditada con prompt revisor.

Comandos disponibles:

* `/start`: Inicio y menú interactivo.
* `/help`: Ayuda con botones inline.
* `/equipos`: Ver lista de equipos disponibles.
* `/stats`: Estado del bot, cache, IA y APIs.

El bot usa un JSON centralizado (`mcp_futbol_data.json`) con:

* Configuración de prompts.
* Alias de equipos.
* Claves de ligas.
* Mensajes de ayuda.
* Menús interactivos y respuestas personalizadas.

Ejemplos de consultas:

* *"Real Madrid próximos partidos"*
* *"Análisis de Premier League"*
* *"¿Quién ganará el clásico español?"*

Cada interacción queda registrada en logs para análisis posterior.

---

## 🚫 Seguridad y Variables Sensibles

El archivo `.env` contiene claves de APIs, tokens y URL del modelo LLM:

```env
FOOTBALL_API_KEY=...
TELEGRAM_BOT_TOKEN=...
LLM_API_URL=http://localhost:1234/v1/chat/completions
LLM_MODEL=mistral-7b-instruct-v0.1
```

> ❌ Este archivo **no debe subirse**. Se provee `.env.example` como referencia.

---

## 📚 Instrucciones de Instalación

```bash
# Clonar repositorio
https://github.com/Pabandres85/MCP_IA.git
cd MCP_IA

# Crear y activar entorno virtual (opcional)
python -m venv venv
source venv/bin/activate  # o venv\Scripts\activate en Windows

# Instalar dependencias
pip install -r requirements.txt

# Agregar archivo .env con tus claves
cp .env.example .env

# Ejecutar supervisord para lanzar el dashboard y el bot
supervisord -c supervisord.conf
```

> Asegúrate de tener LM Studio ejecutando el modelo LLM y habilitando su API local.

---

## 🧠 Modelo de Lenguaje Utilizado

Este proyecto utiliza el modelo **Mathstral 7B v0.1** (GGUF - Q4\_K\_M), una variante de la familia **Mistral AI**, especializada en razonamiento lógico-matemático y tareas complejas multietapa, lo que la convierte en una opción ideal para análisis deportivos estructurados y predicciones contextuales.

### 🗂️ Características del modelo:

* **Nombre completo**: Mathstral 7B v0.1
* **Arquitectura**: Mistral
* **Tamaño**: 7B parámetros
* **Cuantización**: GGUF - Q4\_K\_M (\~4.37 GB)
* **Fuente**: [MistralAI](https://huggingface.co/mistralai)
* **Enlace modelo base**: [mathstral-7B-v0.1](https://huggingface.co/mistralai/mathstral-7B-v0.1)
* **Versión GGUF**: Proporcionada por `bartowski` basada en `llama.cpp`

### 🧬 Capacidades destacadas:

* Excelente para tareas de razonamiento multi-paso.
* Afinado para problemas complejos y contextos estructurados.
* Destacado en tareas de STEM, lo cual favorece la comprensión de patrones deportivos y predicción estratégica.

> Este modelo se ejecuta localmente desde LM Studio y expone una API en formato OpenAI-compatible para facilitar su integración con Streamlit y el bot de Telegram.

---

## 🚀 Proximamente

* Historial de predicciones por fecha
* Panel de administración para edición de prompts
* Integración con otras fuentes deportivas
* Exportación PDF masiva de predicciones

---

## 📍 Autor

**Pabandres85**
GitHub: [@Pabandres85](https://github.com/Pabandres85)
Proyecto desarrollado como prueba de integración de IA local con analítica deportiva.

---

## 📅 Licencia

MIT License — Libre de usar, modificar y compartir.
