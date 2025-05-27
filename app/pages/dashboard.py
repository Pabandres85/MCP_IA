import streamlit as st
import requests
from dotenv import load_dotenv
import os
import pandas as pd
import plotly.express as px
from datetime import date
from app.generate_pdf import generar_pdf
from app.llm_client import ask_llm
from app.injuries_service import obtener_lesiones  
from app.teams_service import obtener_equipos
import json
from datetime import datetime, timedelta
import plotly.graph_objects as go

# Configuración general
st.set_page_config(page_title="MCP Fútbol", layout="wide")
load_dotenv()

api_key = os.getenv("FOOTBALL_API_KEY")
url_base = os.getenv("FOOTBALL_API_URL")
headers = {
    "X-Auth-Token": api_key,
    "Content-Type": "application/json"
}

competition_labels = {
    "WC": "🌍 FIFA World Cup", "CL": "🏆 UEFA Champions League",
    "BL1": "🇩🇪 Bundesliga", "DED": "🇳🇱 Eredivisie",
    "BSA": "🇧🇷 Brasileirao Serie A", "PD": "🇪🇸 La Liga",
    "FL1": "🇫🇷 Ligue 1", "ELC": "🏴 Championship",
    "PPL": "🇵🇹 Primeira Liga", "EC": "🇪🇺 Euro",
    "SA": "🇮🇹 Serie A", "PL": "🏴 Premier League"
}

# Sidebar
st.sidebar.title("Filtros")
selected_label = st.sidebar.selectbox("Competición", list(competition_labels.values()))
code_map = {v: k for k, v in competition_labels.items()}
selected_competition = code_map[selected_label]
start_date, end_date = st.sidebar.date_input("Rango de fechas", value=(date(2025, 4, 1), date(2025, 5, 22)))

# Debug info en sidebar
with st.sidebar.expander("🔧 Info de Debug"):
    st.code(f"Competición: {selected_competition}")
    st.code(f"API Key: {api_key[:10] if api_key else 'NO ENCONTRADA'}...")
    st.code(f"URL Base: {url_base}")

# API partidos históricos con debug mejorado
url = f"{url_base}competitions/{selected_competition}/matches?dateFrom={start_date}&dateTo={end_date}"

try:
    response = requests.get(url, headers=headers, timeout=10)
    
    # Debug en sidebar
    with st.sidebar.expander("📡 Respuesta API"):
        st.code(f"Status: {response.status_code}")
        st.code(f"URL: {url}")
        if response.status_code != 200:
            st.code(f"Error: {response.text[:200]}")
    
except requests.exceptions.RequestException as e:
    st.error(f"Error de conexión: {e}")
    response = None

def obtener_proximos_partidos(codigo_competencia):
    url_prox = f"{url_base}competitions/{codigo_competencia}/matches?status=SCHEDULED"
    try:
        response = requests.get(url_prox, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("matches", [])[:10]
    except:
        pass
    return []

matches = []
df_matches = pd.DataFrame()

if response and response.status_code == 200:
    try:
        data = response.json()
        matches = data.get("matches", [])
        
        if matches:
            df_matches = pd.DataFrame([{
                "Fecha": match["utcDate"][:10],
                "Equipo Local": match["homeTeam"]["name"],
                "Equipo Visitante": match["awayTeam"]["name"],
                "Goles Local": match["score"]["fullTime"]["home"],
                "Goles Visitante": match["score"]["fullTime"]["away"],
                "Estado": match["status"]
            } for match in matches])
            st.success(f"✅ {len(matches)} partidos cargados correctamente")
        else:
            st.warning(f"⚠️ No hay partidos para {selected_label} en las fechas seleccionadas")
            
    except Exception as e:
        st.error(f"Error procesando respuesta JSON: {e}")

elif response and response.status_code == 400:
    st.error("❌ Error 400: Petición incorrecta")
    try:
        error_data = response.json()
        st.code(f"Detalles: {error_data}")
    except:
        st.code(f"Respuesta: {response.text}")
    
    st.info("💡 **Posibles soluciones:**")
    st.write("- Intenta cambiar a **Premier League** o **La Liga**")
    st.write("- Verifica que las fechas sean válidas")
    st.write("- La competición seleccionada puede no tener partidos en esas fechas")
    
elif response and response.status_code == 403:
    st.error("❌ Error 403: API Key inválida o sin permisos")
    st.info("Verifica tu API Key en el archivo .env")
    
elif response and response.status_code == 429:
    st.error("❌ Error 429: Límite de requests excedido")
    st.info("Espera un momento antes de hacer otra consulta")
    
else:
    st.error(f"❌ Error al consultar la API: {response.status_code if response else 'Sin respuesta'}")

# ✅ TABS CORREGIDOS - UNA SOLA DECLARACIÓN
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏟️ Partidos", "📊 Estadísticas globales", "🔍 Por equipo",
    "🤖 Análisis con LLM", "📥 Exportar", "🔮 Predicción por equipo",
    "📱 Telegram Metrics"  # NUEVO TAB
])

# TAB 1 - Partidos
with tab1:
    st.title("📅 Partidos")
    if not df_matches.empty:
        st.dataframe(df_matches, use_container_width=True)
    else:
        st.warning("No se encontraron partidos.")

# TAB 2 - Estadísticas globales
with tab2:
    st.title("📊 Estadísticas Globales")
    if not df_matches.empty:
        total_partidos = len(df_matches)
        total_goles = df_matches["Goles Local"].sum() + df_matches["Goles Visitante"].sum()
        empates = df_matches[df_matches["Goles Local"] == df_matches["Goles Visitante"]].shape[0]
        ganadores = total_partidos - empates

        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Partidos", total_partidos)
        col2.metric("Total de Goles", total_goles)
        col3.metric("Empates vs Definidos", f"{empates} 🟰 {ganadores}")

        goal_data = pd.concat([
            df_matches[["Equipo Local", "Goles Local"]].rename(columns={"Equipo Local": "Equipo", "Goles Local": "Goles"}),
            df_matches[["Equipo Visitante", "Goles Visitante"]].rename(columns={"Equipo Visitante": "Equipo", "Goles Visitante": "Goles"})
        ])
        goal_totals = goal_data.groupby("Equipo")["Goles"].sum().reset_index()

        st.subheader("🥅 Goles por Equipo")
        fig = px.bar(goal_totals.sort_values("Goles"), x="Goles", y="Equipo", orientation="h", text="Goles", height=500)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("⚖️ Probabilidad de Goles por Equipo")
        goal_totals["Probabilidad (%)"] = 100 * goal_totals["Goles"] / total_goles
        fig_prob = px.pie(goal_totals, values="Probabilidad (%)", names="Equipo", title="Distribución de goles")
        st.plotly_chart(fig_prob, use_container_width=True)

        st.subheader("🧠 Predicción general con IA")
        if st.toggle("Activar análisis inteligente del torneo", value=False):
            st.info("La IA analizará el torneo y ofrecerá un resumen predictivo.")
            prompt = (
                "Analiza el rendimiento de los equipos según esta tabla de resultados e indica: "
                "1) los más consistentes, 2) posibles sorpresas y 3) predicciones de desempeño futuro."
            )
            contexto = df_matches.to_string(index=False)
            with st.spinner("🧠 Consultando IA..."):
                respuesta = ask_llm(prompt, contexto)
            st.markdown("### 📋 Resumen del modelo")
            st.markdown(respuesta)

            pdf = generar_pdf(respuesta, titulo="Análisis general del torneo")
            st.download_button("📄 Descargar análisis en PDF", data=pdf,
                               file_name="analisis_general_torneo.pdf", mime="application/pdf")
    else:
        st.info("Selecciona una competición con datos disponibles para ver estadísticas")

# TAB 3 - Por equipo
with tab3:
    st.title("🔍 Estadísticas por Equipo")

    league_ids = {
        "PD": 140, "PL": 39, "SA": 135, "BSA": 71, "BL1": 78, "FL1": 61,
    }

    if not df_matches.empty:
        equipos_disponibles = sorted(set(df_matches["Equipo Local"]).union(df_matches["Equipo Visitante"]))
        selected_team = st.selectbox("Selecciona un equipo", equipos_disponibles)

        team_matches = df_matches[
            (df_matches["Equipo Local"] == selected_team) | (df_matches["Equipo Visitante"] == selected_team)
        ]

        goles_anotados = (
            df_matches.loc[df_matches["Equipo Local"] == selected_team, "Goles Local"].sum() +
            df_matches.loc[df_matches["Equipo Visitante"] == selected_team, "Goles Visitante"].sum()
        )
        goles_recibidos = (
            df_matches.loc[df_matches["Equipo Local"] == selected_team, "Goles Visitante"].sum() +
            df_matches.loc[df_matches["Equipo Visitante"] == selected_team, "Goles Local"].sum()
        )

        st.metric("Partidos jugados", len(team_matches))
        st.metric("Goles anotados", goles_anotados)
        st.metric("Goles recibidos", goles_recibidos)

        st.subheader("📄 Detalle de partidos del equipo")
        st.dataframe(team_matches, use_container_width=True)
    else:
        st.info("No hay datos históricos disponibles para mostrar estadísticas.")
        selected_team = None

    selected_code = code_map[selected_label]
    league_id = league_ids.get(selected_code)

    if league_id and selected_team:
        team_ids, status_equipos = obtener_equipos(league_id)
        if status_equipos == 200 and selected_team in team_ids:
            team_id = team_ids[selected_team]
            st.subheader("🚑 Estado de jugadores")
            lesiones, status_lesion = obtener_lesiones(team_id)
            if status_lesion == 200 and lesiones:
                for lesion in lesiones:
                    jugador = lesion['player']['name']
                    posicion = lesion['player']['position']
                    tipo = lesion['type']
                    fecha = lesion['fixture']['date'][:10] if lesion.get('fixture') else "Fecha desconocida"
                    st.markdown(f"- **{jugador}** ({posicion}) – {tipo}, desde {fecha}")
            elif status_lesion == 200:
                st.info("No se registran jugadores lesionados o suspendidos.")
            else:
                st.warning("No se pudo consultar la información de lesiones.")
        else:
            st.info("🔒 Solo se pueden mostrar lesiones para algunas ligas con RapidAPI.")

# TAB 4 - Análisis con LLM
with tab4:
    st.title("🤖 Análisis con LLM (IA local)")

    if not df_matches.empty:
        st.markdown("Escribe tu pregunta personalizada")
        pregunta_personalizada = st.text_area(" ", placeholder="Ej. ¿Qué equipo mostró mejor rendimiento defensivo?", height=100)
        col_enviar, _ = st.columns([0.3, 0.7])
        enviar_pregunta = col_enviar.button("💬 Enviar pregunta")

        st.markdown("### 📌 Preguntas rápidas")
        if st.button("📊 ¿Qué equipo anotó más goles?"):
            pregunta_personalizada = "¿Cuál fue el equipo que más goles anotó en este periodo?"
        if st.button("🛫 ¿Quién fue el mejor visitante?"):
            pregunta_personalizada = "¿Qué equipo tuvo mejor rendimiento como visitante?"
        if st.button("🧠 Dame un resumen del torneo"):
            pregunta_personalizada = "Haz un resumen del rendimiento de todos los equipos."
        if st.button("🧮 Predicción de equipo ganador"):
            pregunta_personalizada = "Según los datos, ¿qué equipo tiene más probabilidad de ganar los próximos partidos?"

        if pregunta_personalizada and enviar_pregunta:
            contexto = df_matches.to_string(index=False)
            with st.spinner("🧠 Analizando con IA, por favor espera..."):
                respuesta = ask_llm(pregunta_personalizada, contexto)
                st.success("🧠 Respuesta del modelo:")
                st.markdown(respuesta)

                pdf = generar_pdf(respuesta, titulo="Análisis LLM")
                st.download_button("📄 Descargar análisis como PDF", data=pdf,
                                   file_name="analisis_llm.pdf", mime="application/pdf")
    else:
        st.warning("No hay datos disponibles para analizar.")

# TAB 5 - Exportar
with tab5:
    st.title("📥 Exportar")
    if not df_matches.empty:
        st.download_button("📄 CSV", df_matches.to_csv(index=False), file_name="partidos.csv", mime="text/csv")
        st.download_button("📄 JSON", df_matches.to_json(orient="records"), file_name="partidos.json", mime="application/json")
    else:
        st.warning("No hay datos para exportar.")

# TAB 6 - Predicción por equipo
with tab6:
    st.title("🔮 Predicción por equipo")
    partidos_futuros = obtener_proximos_partidos(selected_competition)

    if partidos_futuros:
        equipos_unicos = set()
        comparacion = []

        for partido in partidos_futuros:
            local = partido["homeTeam"]["name"]
            visitante = partido["awayTeam"]["name"]
            fecha = partido["utcDate"][:10]
            equipos_unicos.update([local, visitante])

            with st.expander(f"{fecha} - {local} vs {visitante}"):
                if st.button(f"🔍 Generar predicción para {local} vs {visitante}", key=f"{local}_{visitante}_{fecha}"):
                    contexto = df_matches[
                        (df_matches["Equipo Local"].isin([local, visitante])) |
                        (df_matches["Equipo Visitante"].isin([local, visitante]))
                    ]

                    if not contexto.empty:
                        prompt = (
                            f"Basado en los datos, ¿cuál es tu predicción para el partido entre {local} y {visitante}? "
                            f"Indica fortalezas, debilidades y di: 'El posible ganador es: EQUIPO'."
                        )

                        with st.spinner("🔮 Generando predicción con IA..."):
                            resumen = ask_llm(prompt, contexto.to_string(index=False))

                        st.markdown("### 📋 Resultado del análisis:")
                        st.markdown(resumen)

                        for linea in resumen.splitlines():
                            if "El posible ganador es:" in linea:
                                st.success(f"🏆 {linea.strip()}")
                                break

                        pdf = generar_pdf(resumen, titulo=f"Predicción {local} vs {visitante}")
                        st.download_button("📄 Descargar como PDF", data=pdf,
                                           file_name=f"prediccion_{local}_vs_{visitante}.pdf", mime="application/pdf")

                        st.plotly_chart(
                            px.pie(names=[local, visitante, "Empate"], values=[40, 35, 25],
                                   title="Probabilidad estimada"),
                            use_container_width=True
                        )

                        comparacion.append({
                            "Equipo": local,
                            "Oponente": visitante,
                            "Fecha": fecha,
                            "Predicción": resumen
                        })
                    else:
                        st.warning("No hay suficientes datos históricos para este partido.")

        st.subheader("📊 Comparación de próximos equipos")
        seleccionados = st.multiselect("Selecciona equipos para comparar", sorted(equipos_unicos))

        resumen_comparado = []
        for equipo in seleccionados:
            encuentros = [m for m in partidos_futuros if equipo in (m["homeTeam"]["name"], m["awayTeam"]["name"])]
            if encuentros:
                rival = encuentros[0]["awayTeam"]["name"] if equipo == encuentros[0]["homeTeam"]["name"] else encuentros[0]["homeTeam"]["name"]
                fecha = encuentros[0]["utcDate"][:10]
                contexto_eq = df_matches[
                    (df_matches["Equipo Local"] == equipo) | (df_matches["Equipo Visitante"] == equipo)
                ]
                with st.spinner(f"🤖 Analizando predicción de {equipo} vs {rival}..."):
                    pred = ask_llm(f"¿Qué se espera del próximo partido de {equipo} contra {rival}? "
                                   f"Responde incluyendo 'El posible ganador es:'", contexto_eq.to_string(index=False))
                resumen_comparado.append({
                    "Equipo": equipo,
                    "Oponente": rival,
                    "Fecha": fecha,
                    "Predicción": pred
                })

        if resumen_comparado:
            df_comparacion = pd.DataFrame(resumen_comparado)
            st.dataframe(df_comparacion)

            pdf_comparacion = generar_pdf(
                "\n\n".join([f"{r['Equipo']} vs {r['Oponente']} ({r['Fecha']}):\n{r['Predicción']}" for r in resumen_comparado]),
                titulo="Comparación de predicciones"
            )
            st.download_button("📄 Descargar comparativo PDF", data=pdf_comparacion,
                               file_name="comparacion_equipos.pdf", mime="application/pdf")
    else:
        st.warning("No hay partidos programados próximamente.")

# TAB 7 - Telegram Metrics
with tab7:
    st.title("📱 Métricas del Bot de Telegram")
    
    # Función para cargar datos de Telegram
    @st.cache_data(ttl=300)  # Cache por 5 minutos
    def cargar_datos_telegram():
        """Carga datos del bot de Telegram desde múltiples fuentes"""
        datos = {}
        
        # 1. Logs de interacciones
        log_paths = [
            "logs/interacciones.csv", 
            "app/logs/interacciones.csv",
            "../logs/interacciones.csv"
        ]
        
        for path in log_paths:
            if os.path.exists(path):
                try:
                    datos['interacciones'] = pd.read_csv(path)
                    st.success(f"✅ Datos cargados desde: {path}")
                    break
                except Exception as e:
                    st.warning(f"Error cargando {path}: {e}")
        
        # 2. Estado del sistema
        system_paths = [
            "logs/system_status.json",
            "app/logs/system_status.json", 
            "../logs/system_status.json"
        ]
        
        for path in system_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        datos['sistema'] = json.load(f)
                    break
                except Exception as e:
                    pass
        
        # 3. Métricas de rendimiento
        performance_paths = [
            "logs/performance.json",
            "app/logs/performance.json",
            "../logs/performance.json"
        ]
        
        for path in performance_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        datos['rendimiento'] = json.load(f)
                    break
                except Exception as e:
                    pass
        
        return datos

    # Cargar datos
    datos_telegram = cargar_datos_telegram()
    
    if 'interacciones' not in datos_telegram:
        st.warning("❌ No se encontraron datos de interacciones del bot de Telegram")
        st.info("💡 **Para ver métricas:**")
        st.write("1. Asegúrate de que el bot esté funcionando")
        st.write("2. Verifica que exista el archivo `logs/interacciones.csv`")
        st.write("3. Realiza algunas consultas al bot de Telegram")
        
        # Mostrar ejemplo de estructura esperada
        st.subheader("📋 Estructura esperada del archivo CSV:")
        ejemplo_df = pd.DataFrame({
            'timestamp': ['2024-05-23 10:30:00', '2024-05-23 10:31:00'],
            'user_id': ['usuario1', 'usuario2'],
            'mensaje': ['Real Madrid próximos partidos', 'hola'],
            'respuesta': ['Análisis del Real Madrid...', 'Hola! Soy tu bot...'],
            'liga': ['PD', None]
        })
        st.dataframe(ejemplo_df)
        
    else:
        df_telegram = datos_telegram['interacciones']
        
        # Procesar timestamps si existen
        if 'timestamp' in df_telegram.columns:
            try:
                df_telegram['timestamp'] = pd.to_datetime(df_telegram['timestamp'])
                df_telegram['fecha'] = df_telegram['timestamp'].dt.date
                df_telegram['hora'] = df_telegram['timestamp'].dt.hour
                df_telegram['dia_semana'] = df_telegram['timestamp'].dt.day_name()
            except:
                st.warning("⚠️ Error procesando timestamps")
        
        # ===== MÉTRICAS PRINCIPALES =====
        st.header("📊 Métricas Generales del Bot")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_usuarios = df_telegram['user_id'].nunique() if 'user_id' in df_telegram.columns else 0
            st.metric("👥 Usuarios Únicos", total_usuarios)
        
        with col2:
            total_mensajes = len(df_telegram)
            st.metric("💬 Total Mensajes", total_mensajes)
        
        with col3:
            if 'liga' in df_telegram.columns:
                consultas_liga = df_telegram[df_telegram['liga'].notna()].shape[0]
                st.metric("⚽ Consultas de Liga", consultas_liga)
            else:
                st.metric("⚽ Consultas de Liga", "N/A")
        
        with col4:
            if total_usuarios > 0:
                promedio = round(total_mensajes / total_usuarios, 1)
                st.metric("📈 Promedio/Usuario", promedio)
            else:
                st.metric("📈 Promedio/Usuario", "0")
        
        # ===== GRÁFICOS DE ACTIVIDAD =====
        if 'timestamp' in df_telegram.columns and 'hora' in df_telegram.columns:
            st.header("📈 Patrones de Uso")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Actividad por hora
                if 'hora' in df_telegram.columns:
                    actividad_hora = df_telegram.groupby('hora').size().reset_index(name='mensajes')
                    fig_hora = px.bar(
                        actividad_hora, 
                        x='hora', 
                        y='mensajes',
                        title="🕐 Actividad por Hora del Día",
                        color='mensajes',
                        color_continuous_scale='viridis'
                    )
                    fig_hora.update_layout(
                        xaxis_title="Hora del día",
                        yaxis_title="Número de mensajes"
                    )
                    st.plotly_chart(fig_hora, use_container_width=True)
            
            with col2:
                # Actividad por día de la semana
                if 'dia_semana' in df_telegram.columns:
                    dias_orden = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    actividad_dia = df_telegram.groupby('dia_semana').size().reindex(dias_orden).reset_index(name='mensajes')
                    actividad_dia['dia_semana'] = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
                    
                    fig_dia = px.bar(
                        actividad_dia, 
                        x='dia_semana', 
                        y='mensajes',
                        title="📅 Actividad por Día de la Semana",
                        color='mensajes',
                        color_continuous_scale='blues'
                    )
                    st.plotly_chart(fig_dia, use_container_width=True)
            
            # Línea de tiempo de actividad
            if 'fecha' in df_telegram.columns:
                actividad_fecha = df_telegram.groupby('fecha').size().reset_index(name='mensajes')
                fig_timeline = px.line(
                    actividad_fecha, 
                    x='fecha', 
                    y='mensajes',
                    title="📊 Evolución de Mensajes en el Tiempo",
                    markers=True
                )
                fig_timeline.update_layout(
                    xaxis_title="Fecha",
                    yaxis_title="Mensajes por día"
                )
                st.plotly_chart(fig_timeline, use_container_width=True)
        
        # ===== ANÁLISIS DE USUARIOS =====
        st.header("👥 Análisis de Usuarios")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'user_id' in df_telegram.columns:
                user_counts = df_telegram['user_id'].value_counts().head(10).reset_index()
                user_counts.columns = ["Usuario", "Mensajes"]
                
                fig_users = px.bar(
                    user_counts, 
                    x="Usuario", 
                    y="Mensajes", 
                    title="🏆 Top 10 Usuarios Más Activos",
                    color="Mensajes",
                    color_continuous_scale="blues"
                )
                fig_users.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_users, use_container_width=True)
        
        with col2:
            if 'liga' in df_telegram.columns and df_telegram['liga'].notna().any():
                liga_counts = df_telegram[df_telegram['liga'].notna()]['liga'].value_counts().reset_index()
                liga_counts.columns = ["Liga", "Consultas"]
                
                # Mapear códigos a nombres amigables
                liga_nombres = {
                    'PD': 'La Liga 🇪🇸',
                    'PL': 'Premier League 🏴󠁧󠁢󠁥󠁮󠁧󠁿',
                    'SA': 'Serie A 🇮🇹',
                    'BL1': 'Bundesliga 🇩🇪',
                    'FL1': 'Ligue 1 🇫🇷',
                    'BSA': 'Brasileirao 🇧🇷',
                    'personalizada': 'Consultas Personales 👤'
                }
                
                liga_counts['Liga_Nombre'] = liga_counts['Liga'].map(liga_nombres).fillna(liga_counts['Liga'])
                
                fig_ligas = px.pie(
                    liga_counts, 
                    values="Consultas", 
                    names="Liga_Nombre", 
                    title="⚽ Distribución por Liga"
                )
                st.plotly_chart(fig_ligas, use_container_width=True)
        
        # ===== ESTADO DEL SISTEMA =====
        if 'sistema' in datos_telegram:
            st.header("🖥️ Estado del Sistema")
            sistema = datos_telegram['sistema']
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                status_api = sistema.get('api_football', 'unknown')
                color = "🟢" if status_api == "online" else "🔴"
                st.metric(f"{color} API Football", status_api.upper())
            
            with col2:
                status_ia = sistema.get('llm_local', 'unknown')
                color = "🟢" if status_ia == "online" else "🔴"
                st.metric(f"{color} IA Local", status_ia.upper())
            
            with col3:
                cache_entries = sistema.get('cache_entries', 0)
                st.metric("💾 Cache Entries", cache_entries)
            
            with col4:
                cpu_usage = sistema.get('cpu_usage', 0)
                st.metric("🔧 CPU Usage", f"{cpu_usage}%")
        
        # ===== MÉTRICAS DE RENDIMIENTO =====
        if 'rendimiento' in datos_telegram:
            st.header("⚡ Métricas de Rendimiento")
            rendimiento = datos_telegram['rendimiento']
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                tiempo_respuesta = rendimiento.get('tiempo_promedio_respuesta', 0)
                color = "🟢" if tiempo_respuesta < 2 else "🟡" if tiempo_respuesta < 5 else "🔴"
                st.metric(f"{color} Tiempo Respuesta", f"{tiempo_respuesta}s")
            
            with col2:
                llamadas_api = rendimiento.get('llamadas_api_hoy', 0)
                st.metric("🌐 API Calls Hoy", llamadas_api)
            
            with col3:
                cache_hit_rate = rendimiento.get('cache_hit_rate', 0)
                color = "🟢" if cache_hit_rate > 70 else "🟡" if cache_hit_rate > 40 else "🔴"
                st.metric(f"{color} Cache Hit Rate", f"{cache_hit_rate}%")
        
        # ===== ANÁLISIS DE MENSAJES =====
        st.header("💬 Análisis de Mensajes")
        
        if 'mensaje' in df_telegram.columns:
            # Palabras más comunes en consultas
            todos_mensajes = ' '.join(df_telegram['mensaje'].astype(str)).lower()
            palabras_futbol = ['real madrid', 'barcelona', 'manchester', 'liverpool', 'arsenal', 
                             'próximos', 'partidos', 'análisis', 'predicción', 'liga']
            
            contador_palabras = {}
            for palabra in palabras_futbol:
                contador_palabras[palabra] = todos_mensajes.count(palabra)
            
            if any(contador_palabras.values()):
                palabras_df = pd.DataFrame(list(contador_palabras.items()), 
                                         columns=['Palabra', 'Frecuencia'])
                palabras_df = palabras_df[palabras_df['Frecuencia'] > 0].sort_values('Frecuencia', ascending=True)
                
                if not palabras_df.empty:
                    fig_palabras = px.bar(
                        palabras_df, 
                        x='Frecuencia', 
                        y='Palabra',
                        orientation='h',
                        title="🔤 Términos Más Consultados",
                        color='Frecuencia',
                        color_continuous_scale='reds'
                    )
                    st.plotly_chart(fig_palabras, use_container_width=True)
        
        # ===== TABLA DE INTERACCIONES RECIENTES =====
        st.header("📋 Interacciones Recientes")
        
        # Filtros
        col1, col2 = st.columns(2)
        
        with col1:
            if 'user_id' in df_telegram.columns:
                usuarios_unicos = ["Todos"] + list(df_telegram['user_id'].unique())
                filtro_usuario = st.selectbox("👤 Filtrar por usuario:", usuarios_unicos)
        
        with col2:
            if 'liga' in df_telegram.columns:
                ligas_unicas = ["Todas"] + list(df_telegram['liga'].dropna().unique())
                filtro_liga = st.selectbox("⚽ Filtrar por liga:", ligas_unicas)
        
        # Aplicar filtros
        df_filtrado = df_telegram.copy()
        if 'filtro_usuario' in locals() and filtro_usuario != "Todos":
            df_filtrado = df_filtrado[df_filtrado['user_id'] == filtro_usuario]
        if 'filtro_liga' in locals() and filtro_liga != "Todas":
            df_filtrado = df_filtrado[df_filtrado['liga'] == filtro_liga]
        
        # Mostrar últimas 20 interacciones
        df_recientes = df_filtrado.tail(20)
        st.dataframe(df_recientes, use_container_width=True)
        
        # ===== EXPORTAR DATOS =====
        st.header("📥 Exportar Datos de Telegram")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv_data = df_filtrado.to_csv(index=False)
            st.download_button(
                "📄 Descargar CSV",
                csv_data,
                file_name=f"telegram_metrics_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col2:
            json_data = df_filtrado.to_json(orient="records", indent=2)
            st.download_button(
                "🧾 Descargar JSON",
                json_data,
                file_name=f"telegram_metrics_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
        
        with col3:
            # Crear resumen estadístico
            resumen = f"""
            RESUMEN DE MÉTRICAS DEL BOT DE TELEGRAM
            =====================================
            
            Usuarios únicos: {total_usuarios}
            Total de mensajes: {total_mensajes}
            Consultas de liga: {consultas_liga if 'liga' in df_telegram.columns else 'N/A'}
            Promedio mensajes/usuario: {promedio if total_usuarios > 0 else 0}
            
            Período analizado: {df_telegram['fecha'].min() if 'fecha' in df_telegram.columns else 'N/A'} - {df_telegram['fecha'].max() if 'fecha' in df_telegram.columns else 'N/A'}
            """
            
            st.download_button(
                "📊 Resumen TXT",
                resumen,
                file_name=f"resumen_telegram_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain"
            )