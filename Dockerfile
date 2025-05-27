FROM python:3.11

# Crear y trabajar en el directorio de la app
WORKDIR /app

# Copiar archivos
COPY . .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Instalar supervisord explícitamente
RUN apt-get update && apt-get install -y supervisor

# Exponer el puerto de streamlit
EXPOSE 8501

# Iniciar supervisord
CMD ["supervisord", "-c", "supervisord.conf"]








