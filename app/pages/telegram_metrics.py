import streamlit as st
import pandas as pd
import plotly.express as px
import os



st.set_page_config(page_title="📈 Métricas de Telegram", layout="wide")

st.title("📊 Métricas del Bot de Telegram")

# Ruta del archivo CSV
log_path = "logs/interacciones.csv"

log_path_alt = "app/logs/interacciones.csv"
if not os.path.exists(log_path) and os.path.exists(log_path_alt):
    log_path = log_path_alt

if not os.path.exists(log_path):
    st.warning("❌ Aún no se han registrado interacciones con el bot.")
else:
    df = pd.read_csv(log_path)

    st.subheader("🗂️ Registros de Interacciones")
    st.dataframe(df, use_container_width=True)

    st.subheader("📈 Interacciones por Usuario")
    user_counts = df["user_id"].value_counts().reset_index()
    user_counts.columns = ["Usuario", "Cantidad"]
    fig_users = px.bar(user_counts, x="Usuario", y="Cantidad", title="Mensajes por Usuario")
    st.plotly_chart(fig_users, use_container_width=True)

    st.subheader("⚽ Interacciones por Liga (cuando aplica)")
    if "liga" in df.columns:
        liga_counts = df["liga"].value_counts().reset_index()
        liga_counts.columns = ["Liga", "Mensajes"]
        fig_ligas = px.pie(liga_counts, values="Mensajes", names="Liga", title="Distribución por Liga")
        st.plotly_chart(fig_ligas, use_container_width=True)

    st.subheader("⬇️ Exportar logs")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📄 Descargar CSV", df.to_csv(index=False), file_name="interacciones_bot.csv", mime="text/csv")
    with col2:
        st.download_button("🧾 Descargar JSON", df.to_json(orient="records", indent=2), file_name="interacciones_bot.json", mime="application/json")
