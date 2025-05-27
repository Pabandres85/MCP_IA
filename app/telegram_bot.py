import os
import requests
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes,
    filters, CallbackContext, CallbackQueryHandler
)
import json
import time

# === CARGA DE CONFIGURACIÓN DESDE JSON CENTRALIZADO ===
RUTA_JSON = os.path.join(os.path.dirname(__file__), "data", "mcp_futbol_data.json")
if not os.path.exists(RUTA_JSON):
    raise FileNotFoundError(f"❌ No se encontró el archivo JSON en: {RUTA_JSON}")

try:
    with open(RUTA_JSON, encoding="utf-8") as f:
        config = json.load(f)
    print("✅ JSON cargado correctamente.")
except Exception as e:
    print(f"❌ Error leyendo el JSON: {e}")
    raise

# Variables globales, bien cargadas
respuestas_personalizadas = config.get("respuestas_personalizadas", {})
leagues = config.get("leagues", {})
league_context = config.get("league_context", {})
equipos_ligas = config.get("equipos_ligas", {})
palabras_futbol = config.get("palabras_futbol", [])
prompts = config.get("prompts", {})
teclado_principal = config.get("teclado_principal", [])
ayuda_mensaje = config.get("ayuda_mensaje", {})

# Ya puedes usarlas aquí
print(f"🎯 Respuestas personalizadas: {len(respuestas_personalizadas)}")
print("📝 Keys principales:", list(config.keys()))


# Depuración de keys principales
print("📝 Keys principales:", list(config.keys()))
try:
    print("→ Ejemplo respuesta personalizada:", list(config["respuestas_personalizadas"].keys())[:3])
    print("→ Ejemplo leagues:", config["leagues"])
    print("→ Ejemplo league_context:", list(config["league_context"].keys())[:3])
    print("→ Ejemplo equipos_ligas:", list(config["equipos_ligas"].keys())[:3])
    print("→ Ejemplo palabras_futbol:", config["palabras_futbol"][:3])
    print("→ Ejemplo prompts:", list(config["prompts"].keys())[:3])
    print("→ Ejemplo teclado_principal:", config["teclado_principal"])
    print("→ Ejemplo ayuda_mensaje:", list(config["ayuda_mensaje"].keys())[:3])
except Exception as e:
    print("❌ Error accediendo a las keys esperadas del JSON:", e)


# === CARGA DE LLAMADAS EXTERNAS (IA, LOGGING) ===
print("🔧 Cargando dependencias...")
try:
    from app.llm_client import ask_llm
    print("✅ llm_client importado correctamente")
except Exception as e:
    print(f"❌ Error importando llm_client: {e}")

try:
    from app.logger_service import registrar_interaccion
    print("✅ logger_service importado correctamente")
except Exception as e:
    print(f"❌ Error importando logger_service: {e}")
    def registrar_interaccion(usuario, mensaje, respuesta, liga=None):
        print(f"📝 Log: {usuario} - {mensaje[:50]}...")

# === ENV Y CONFIG EXTERNA ===
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
FOOTBALL_API_URL = os.getenv("FOOTBALL_API_URL")

headers = {"X-Auth-Token": FOOTBALL_API_KEY} if FOOTBALL_API_KEY else {}

cache_datos = {}
CACHE_DURACION = 1800  # 30 minutos

def obtener_cache(clave):
    if clave in cache_datos:
        timestamp, datos = cache_datos[clave]
        if time.time() - timestamp < CACHE_DURACION:
            return datos
    return None

def guardar_cache(clave, datos):
    cache_datos[clave] = (time.time(), datos)

# === FUNCIONES GENERALES (Prompts y Respuestas desde JSON) ===

def crear_prompt(tipo, **kwargs):
    """Crea un prompt a partir del template en el JSON y kwargs dinámicos"""
    plantilla = prompts.get(tipo)
    if not plantilla:
        return f"Consulta sobre fútbol: {kwargs.get('user_input','')}"
    return plantilla.format(**kwargs)

def revisar_respuesta_llm(consulta_usuario, respuesta_bot):
    """
    Llama al LLM usando el prompt 'revisor' definido en el JSON para auditar la respuesta generada.
    Devuelve el texto del veredicto y sugerencia si aplica.
    """
    prompt_revisor = crear_prompt("revisor",
        consulta_usuario=consulta_usuario,
        respuesta_bot=respuesta_bot
    )
    resultado_revision = ask_llm(prompt_revisor)
    return resultado_revision


def buscar_respuesta_personalizada(texto):
    texto_lower = texto.lower().strip()
    # Coincidencia exacta
    if texto_lower in respuestas_personalizadas:
        return respuestas_personalizadas[texto_lower]
    # Buscar palabras clave dentro del texto
    for clave, respuesta in respuestas_personalizadas.items():
        if clave in texto_lower:
            return respuesta
    return None

def es_consulta_futbolistica(texto):
    texto_lower = texto.lower().strip()
    return any(palabra in texto_lower for palabra in palabras_futbol)

def detectar_equipo_y_liga(texto):
    texto_lower = texto.lower()
    for equipo, datos in equipos_ligas.items():
        # Busca coincidencia exacta o alias del equipo
        alias = datos.get("alias", [])
        if isinstance(alias, str):
            alias = [alias]
        nombres_posibles = [equipo.lower()] + [a.lower() for a in alias]
        if any(nombre in texto_lower for nombre in nombres_posibles):
            liga = datos.get("liga", "")
            nombre_oficial = datos.get("nombre_oficial", equipo)
            return {
                "detectado": True,
                "equipo": equipo,
                "liga": liga,
                "nombre_oficial": nombre_oficial,
            }
    return {"detectado": False, "equipo": "", "liga": "", "nombre_oficial": ""}



# === FUNCIONES DE API Y PROCESAMIENTO DE DATOS ===

def obtener_proximos_partidos(liga_codigo, limite=5):
    """Obtiene próximos partidos de una liga específica, con cache y validación de fechas"""
    cache_key = f"proximos_{liga_codigo}_{limite}"
    datos_cache = obtener_cache(cache_key)
    if datos_cache:
        datos_validos = limpiar_datos_antiguos(datos_cache)
        if datos_validos:
            return datos_validos
    if not FOOTBALL_API_KEY:
        return []
    try:
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        fecha_limite = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        url = f"{FOOTBALL_API_URL}competitions/{liga_codigo}/matches?dateFrom={fecha_hoy}&dateTo={fecha_limite}&status=SCHEDULED"
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            matches = response.json().get("matches", [])
            matches_validos = limpiar_datos_antiguos(matches)
            matches_finales = matches_validos[:limite]
            if matches_finales:
                guardar_cache(cache_key, matches_finales)
            return matches_finales
        else:
            return []
    except Exception as e:
        print(f"❌ Error obteniendo partidos: {e}")
        return []

def obtener_partidos_recientes(liga_codigo, limite=5):
    """Obtiene partidos recientes de una liga con cache y validación"""
    cache_key = f"recientes_{liga_codigo}_{limite}"
    datos_cache = obtener_cache(cache_key)
    if datos_cache:
        return datos_cache
    if not FOOTBALL_API_KEY:
        return []
    try:
        fecha_fin = datetime.now().strftime("%Y-%m-%d")
        fecha_inicio = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        url = f"{FOOTBALL_API_URL}competitions/{liga_codigo}/matches?dateFrom={fecha_inicio}&dateTo={fecha_fin}&status=FINISHED"
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            matches = response.json().get("matches", [])
            matches_recientes = matches[-limite:] if matches else []
            if matches_recientes:
                guardar_cache(cache_key, matches_recientes)
            return matches_recientes
        else:
            return []
    except Exception as e:
        print(f"❌ Error obteniendo partidos recientes: {e}")
        return []

def buscar_equipo_especifico_mejorado(equipo_info, limite_partidos=8):
    """Versión mejorada de búsqueda de equipo específico"""
    if not equipo_info["detectado"]:
        return None
    liga_codigo = equipo_info["liga"]
    nombre_oficial = equipo_info["nombre_oficial"]
    cache_key = f"equipo_{equipo_info['equipo']}_{liga_codigo}"
    datos_cache = obtener_cache(cache_key)
    if datos_cache:
        return datos_cache
    proximos = obtener_proximos_partidos(liga_codigo, 15)
    recientes = obtener_partidos_recientes(liga_codigo, 15)
    equipo_data = {
        "nombre": nombre_oficial,
        "liga": liga_codigo,
        "proximos": [],
        "recientes": []
    }
    for match in proximos:
        home_team = match.get("homeTeam", {}).get("name", "")
        away_team = match.get("awayTeam", {}).get("name", "")
        if es_mismo_equipo(nombre_oficial, home_team) or es_mismo_equipo(nombre_oficial, away_team):
            equipo_data["proximos"].append(match)
            if len(equipo_data["proximos"]) >= limite_partidos:
                break
    for match in recientes:
        home_team = match.get("homeTeam", {}).get("name", "")
        away_team = match.get("awayTeam", {}).get("name", "")
        if es_mismo_equipo(nombre_oficial, home_team) or es_mismo_equipo(nombre_oficial, away_team):
            equipo_data["recientes"].append(match)
            if len(equipo_data["recientes"]) >= limite_partidos:
                break
    guardar_cache(cache_key, equipo_data)
    return equipo_data

def validar_fecha_partido(fecha_utc):
    """Valida si una fecha de partido es actual (no más de 30 días en el pasado, hasta 1 año futuro)"""
    try:
        if not fecha_utc:
            return False
        fecha_partido = datetime.fromisoformat(fecha_utc.replace('Z', '+00:00'))
        fecha_actual = datetime.now(fecha_partido.tzinfo)
        diferencia_dias = (fecha_partido - fecha_actual).days
        return -30 <= diferencia_dias <= 365
    except Exception as e:
        print(f"Error validando fecha: {e}")
        return False

def limpiar_datos_antiguos(partidos):
    """Filtra partidos con fechas válidas"""
    partidos_validos = []
    for partido in partidos:
        fecha_utc = partido.get("utcDate", "")
        if validar_fecha_partido(fecha_utc):
            partidos_validos.append(partido)
    return partidos_validos

def es_mismo_equipo(nombre_oficial, nombre_api):
    """Determina si dos nombres se refieren al mismo equipo"""
    nombre_oficial_lower = nombre_oficial.lower()
    nombre_api_lower = nombre_api.lower()
    if nombre_oficial_lower == nombre_api_lower:
        return True
    palabras_oficial = set(nombre_oficial_lower.split())
    palabras_api = set(nombre_api_lower.split())
    palabras_comunes = {"fc", "cf", "sc", "ac", "ss", "club", "de", "united", "city"}
    palabras_oficial -= palabras_comunes
    palabras_api -= palabras_comunes
    if not palabras_oficial or not palabras_api:
        return False
    coincidencias = len(palabras_oficial.intersection(palabras_api))
    total_palabras = min(len(palabras_oficial), len(palabras_api))
    return coincidencias / total_palabras >= 0.6

def generar_respuesta_inteligente(equipo_info, datos_equipo, pregunta_original):
    """Genera respuestas más específicas y útiles"""
    if not datos_equipo:
        return f"❌ No encontré información reciente sobre **{equipo_info['nombre_oficial']}** en la API."
    respuesta = f"⚽ **{datos_equipo['nombre']}**\n"
    respuesta += f"🏆 Liga: {league_context.get(datos_equipo['liga'], 'Liga desconocida').split(',')[0]}\n\n"
    # Próximos partidos
    if datos_equipo["proximos"]:
        respuesta += "📅 **Próximos partidos:**\n"
        for i, match in enumerate(datos_equipo["proximos"][:4]):
            try:
                fecha_utc = match.get("utcDate", "")
                if fecha_utc:
                    fecha_obj = datetime.fromisoformat(fecha_utc.replace('Z', '+00:00'))
                    fecha_formateada = fecha_obj.strftime("%d/%m/%Y %H:%M")
                else:
                    fecha_formateada = "Fecha por confirmar"
                home = match["homeTeam"]["name"]
                away = match["awayTeam"]["name"]
                es_local = es_mismo_equipo(equipo_info["nombre_oficial"], home)
                rival = away if es_local else home
                ubicacion = "🏠" if es_local else "✈️"
                respuesta += f"{i+1}. {fecha_formateada} {ubicacion}\n"
                respuesta += f"   **vs {rival}**\n\n"
            except Exception as e:
                print(f"Error procesando partido: {e}")
                continue
    else:
        respuesta += "📅 **Próximos partidos:** No hay partidos programados en los próximos días.\n\n"
    # Resultados recientes y estadísticas
    if datos_equipo["recientes"]:
        respuesta += "📊 **Últimos resultados:**\n"
        victorias = 0
        empates = 0
        derrotas = 0
        goles_favor = 0
        goles_contra = 0
        partidos_mostrar = datos_equipo["recientes"][-6:]
        for match in partidos_mostrar:
            try:
                fecha = match.get("utcDate", "")[:10]
                home = match["homeTeam"]["name"]
                away = match["awayTeam"]["name"]
                score_home = match.get("score", {}).get("fullTime", {}).get("home", 0)
                score_away = match.get("score", {}).get("fullTime", {}).get("away", 0)
                if score_home is None or score_away is None:
                    continue
                es_local = es_mismo_equipo(equipo_info["nombre_oficial"], home)
                goles_equipo = score_home if es_local else score_away
                goles_rival = score_away if es_local else score_home
                rival = away if es_local else home
                ubicacion = "🏠" if es_local else "✈️"
                goles_favor += goles_equipo
                goles_contra += goles_rival
                if goles_equipo > goles_rival:
                    resultado = "✅"
                    victorias += 1
                elif goles_equipo < goles_rival:
                    resultado = "❌"
                    derrotas += 1
                else:
                    resultado = "⚖️"
                    empates += 1
                respuesta += f"{resultado} {ubicacion} vs **{rival}** {goles_equipo}-{goles_rival}\n"
            except Exception as e:
                print(f"Error procesando resultado: {e}")
                continue
        total_partidos = victorias + empates + derrotas
        if total_partidos > 0:
            porcentaje_victorias = round((victorias / total_partidos) * 100, 1)
            promedio_goles = round(goles_favor / total_partidos, 1)
            promedio_recibidos = round(goles_contra / total_partidos, 1)
            respuesta += f"\n📈 **Estadísticas recientes:**\n"
            respuesta += f"• Forma: **{victorias}V-{empates}E-{derrotas}D** ({porcentaje_victorias}% victorias)\n"
            respuesta += f"• Goles: **{promedio_goles}** por partido (promedio)\n"
            respuesta += f"• Recibidos: **{promedio_recibidos}** por partido\n"
            if porcentaje_victorias >= 70:
                forma = "🔥 Excelente forma"
            elif porcentaje_victorias >= 50:
                forma = "👍 Buena forma"
            elif porcentaje_victorias >= 30:
                forma = "⚠️ Forma irregular"
            else:
                forma = "📉 Forma preocupante"
            respuesta += f"• Estado: {forma}\n"
    else:
        respuesta += "📊 **Últimos resultados:** No hay resultados recientes disponibles.\n"
    return respuesta

def formatear_partidos(partidos, tipo="próximos"):
    if not partidos:
        return f"❌ No se encontraron partidos {tipo}."
    resultado = f"**📋 Partidos {tipo}:**\n\n"
    for i, match in enumerate(partidos[:5]):
        try:
            fecha_utc = match.get("utcDate", "")
            if fecha_utc:
                fecha_obj = datetime.fromisoformat(fecha_utc.replace('Z', '+00:00'))
                fecha = fecha_obj.strftime("%d/%m %H:%M")
            else:
                fecha = "Por confirmar"
            home = match["homeTeam"]["name"]
            away = match["awayTeam"]["name"]
            competition = match.get("competition", {}).get("name", "")
            if tipo == "recientes":
                score_home = match.get("score", {}).get("fullTime", {}).get("home")
                score_away = match.get("score", {}).get("fullTime", {}).get("away")
                if score_home is not None and score_away is not None:
                    resultado += f"{i+1}. **{home}** {score_home}-{score_away} **{away}**\n"
                    resultado += f"   📅 {fecha} | 🏆 {competition}\n\n"
                else:
                    resultado += f"{i+1}. **{home}** vs **{away}**\n"
                    resultado += f"   📅 {fecha} | 🏆 {competition}\n\n"
            else:
                resultado += f"{i+1}. **{home}** vs **{away}**\n"
                resultado += f"   📅 {fecha} | 🏆 {competition}\n\n"
        except Exception as e:
            print(f"Error formateando partido: {e}")
            continue
    return resultado

# === MANEJO DE MENSAJES Y COMANDOS (YA USANDO CONFIG JSON) ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"🚀 Comando /start recibido de {update.effective_user.full_name}")
    reply_markup = ReplyKeyboardMarkup(teclado_principal, resize_keyboard=True)
    await update.message.reply_text(
        ayuda_mensaje["bienvenida"],
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def equipos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(ayuda_mensaje["equipos"], parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⚽ Ver Equipos", callback_data="help_equipos")],
        [InlineKeyboardButton("📊 Tipos de Análisis", callback_data="help_analisis")],
        [InlineKeyboardButton("💡 Ejemplos", callback_data="help_ejemplos")],
        [InlineKeyboardButton("🤖 Sobre el Bot", callback_data="help_about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        ayuda_mensaje["ayuda"],
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cache_count = len(cache_datos)
    mensaje_stats = ayuda_mensaje["stats"].format(
        cache_count=cache_count,
        equipos=len(equipos_ligas),
        ligas=len(leagues),
        api="✅ Conectada" if FOOTBALL_API_KEY else "❌ Desconectada",
        ia="✅ Activa" if "ask_llm" in globals() else "❌ Inactiva"
    )
    await update.message.reply_text(mensaje_stats, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "help_equipos":
        await equipos_command(update, context)
    elif query.data == "help_analisis":
        await query.edit_message_text(ayuda_mensaje["tipos_analisis"], parse_mode="Markdown")
    elif query.data == "help_ejemplos":
        await query.edit_message_text(ayuda_mensaje["ejemplos"], parse_mode="Markdown")
    elif query.data == "help_about":
        await query.edit_message_text(ayuda_mensaje["about"], parse_mode="Markdown")

# === MANEJADOR DE MENSAJES PRINCIPAL ===

async def handle_message(update: Update, context: CallbackContext):
    user_input = update.message.text.strip()
    chat_id = update.effective_chat.id
    user_name = update.effective_user.full_name

    print(f"💬 [{chat_id}] Mensaje recibido de {user_name}: '{user_input}'")

    # Manejar botones rápidos
    if user_input == "⚽ Ver Equipos":
        await equipos_command(update, context)
        return
    elif user_input == "❓ Ayuda":
        await help_command(update, context)
        return

    # Respuestas personalizadas
    respuesta_personalizada = buscar_respuesta_personalizada(user_input)
    if respuesta_personalizada:
        await update.message.reply_text(respuesta_personalizada, parse_mode="Markdown")
        try:
            registrar_interaccion(user_name, user_input, respuesta_personalizada, liga="personalizada")
        except Exception as e:
            print(f"❌ Error logging respuesta personalizada: {e}")
        return

      # === NUEVO BLOQUE: Análisis de Ligas CORREGIDO ===
    liga_codigo, liga_nombre = detectar_equipo_y_liga(user_input)
    if liga_codigo:
        mensaje_progreso = await update.message.reply_text(f"🔍 Analizando {liga_nombre}...")
        try:
            partidos_proximos = obtener_proximos_partidos(liga_codigo, 5)
            partidos_recientes = obtener_partidos_recientes(liga_codigo, 5)
            contexto_datos = ""
            contexto_datos += formatear_partidos(partidos_recientes, tipo="recientes") + "\n"
            contexto_datos += formatear_partidos(partidos_proximos, tipo="próximos")
            prompt_liga = crear_prompt(
                "liga",
                liga_nombre=liga_nombre,
                fecha_actual=datetime.now().strftime("%d/%m/%Y"),
                contexto_datos=contexto_datos
            )
            respuesta_ia = ask_llm(prompt_liga)
            await mensaje_progreso.edit_text(f"🏆 **Análisis de {liga_nombre}:**\n\n{respuesta_ia}", parse_mode="Markdown")
            try:
                registrar_interaccion(user_name, user_input, respuesta_ia, liga=liga_codigo)
            except Exception as e:
                print(f"❌ Error logging liga: {e}")
        except Exception as e:
            await mensaje_progreso.edit_text(
                f"⚠️ No se puede conectar al servidor LLM. ¿Está LM Studio ejecutándose?\n\n{e}"
            )
        return


    # --- Equipos específicos, igual que antes ---
    mensaje_progreso = await update.message.reply_text("🧐 Analizando tu consulta...")
    try:
        equipo_info = detectar_equipo_y_liga(user_input)
        if equipo_info["detectado"]:
            datos_equipo = buscar_equipo_especifico_mejorado(equipo_info)
            if datos_equipo and (datos_equipo["proximos"] or datos_equipo["recientes"]):
                respuesta = generar_respuesta_inteligente(equipo_info, datos_equipo, user_input)
                # Preguntas de predicción
                if any(p in user_input.lower() for p in ["prediccion", "analisis", "opinion", "quien", "ganara", "probabilidad"]):
                    prompt_prediccion = crear_prompt("equipo_prediccion",
                        equipo_nombre=equipo_info['nombre_oficial'],
                        user_input=user_input,
                        contexto_equipo=respuesta
                    )
                    prediccion_ia = ask_llm(prompt_prediccion)
                    respuesta += f"\n\n🧠 **Análisis IA:**\n{prediccion_ia}"
                await mensaje_progreso.edit_text(respuesta, parse_mode="Markdown")
                try:
                    registrar_interaccion(user_name, user_input, respuesta, liga=equipo_info["liga"])
                except Exception as e:
                    print(f"❌ Error logging equipo: {e}")
            else:
                contexto_general = f"El usuario pregunta sobre {equipo_info['nombre_oficial']} de {league_context.get(equipo_info['liga'], 'una liga europea')}."
                prompt_general = crear_prompt("general", user_input=user_input, contexto=contexto_general)
                respuesta = ask_llm(prompt_general)
                await mensaje_progreso.edit_text(f"⚽ {respuesta}\n\n💡 *Para datos más específicos, intenta más tarde cuando la API esté disponible.*", parse_mode="Markdown")
                try:
                    registrar_interaccion(user_name, user_input, respuesta, liga=equipo_info["liga"])
                except Exception as e:
                    print(f"❌ Error logging general equipo: {e}")
        else:
            prompt_mejorado = crear_prompt("general", user_input=user_input)
            respuesta = ask_llm(prompt_mejorado)
            await mensaje_progreso.edit_text(f"🧠 **Respuesta:**\n\n{respuesta}", parse_mode="Markdown")
            try:
                registrar_interaccion(user_name, user_input, respuesta, liga="general")
            except Exception as e:
                print(f"❌ Error logging general: {e}")
    except Exception as e:
        print(f"❌ Error procesando consulta: {e}")
        await mensaje_progreso.edit_text(
            "⚠️ Error procesando tu consulta. Por favor, inténtalo de nuevo.\n\n"
            "💡 **Tip:** Prueba con consultas como:\n"
            "• *'Real Madrid próximos partidos'*\n"
            "• *'Análisis de La Liga'*\n"
            "• *'¿Quién ganará el siguiente Clásico?'*"
        )
        try:
            registrar_interaccion(user_name, user_input, "Error procesando consulta", liga="error")
        except Exception as log_error:
            print(f"❌ Error logging error: {log_error}")
#main

def main():
    print("🚀 Iniciando Bot de Fútbol v2.0...")
    print(f"🎯 Respuestas personalizadas: {len(respuestas_personalizadas)}")
    print(f"⚽ Equipos monitoreados: {len(equipos_ligas)}")
    print(f"🏆 Ligas disponibles: {len(leagues)}")
    print(f"📊 API de fútbol: {'✅ Configurada' if FOOTBALL_API_KEY else '❌ No configurada'}")
    print(f"🤖 IA: {'✅ Disponible' if 'ask_llm' in globals() else '❌ No disponible'}")

    if not TELEGRAM_TOKEN:
        print("❌ FATAL: No se encontró TELEGRAM_BOT_TOKEN")
        return

    try:
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("equipos", equipos_command))
        app.add_handler(CommandHandler("stats", stats_command))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        print("✅ Todos los handlers configurados\n🔥 ¡Listo para analizar fútbol!")
        app.run_polling()
    except Exception as e:
        print(f"❌ Error crítico iniciando el bot: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
