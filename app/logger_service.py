import os
import pandas as pd
from datetime import datetime
import threading
import time
import json

# Rutas de logs
LOG_CSV = "logs/interacciones.csv"
LOG_JSON = "logs/interacciones.json"

# Lock para thread safety
log_lock = threading.Lock()

# Asegurar que existe el directorio de logs
os.makedirs("logs", exist_ok=True)

def inicializar_csv():
    """Crea el archivo CSV con headers si no existe o está vacío"""
    with log_lock:
        try:
            if not os.path.exists(LOG_CSV):
                # Crear archivo con headers
                df_inicial = pd.DataFrame(columns=[
                    'timestamp', 'user_id', 'mensaje', 'respuesta', 'liga'
                ])
                df_inicial.to_csv(LOG_CSV, index=False)
                print(f"✅ Creado {LOG_CSV} con headers")
                return
            
            # Verificar si el archivo está vacío o corrupto
            file_size = os.path.getsize(LOG_CSV)
            if file_size == 0:
                df_inicial = pd.DataFrame(columns=[
                    'timestamp', 'user_id', 'mensaje', 'respuesta', 'liga'
                ])
                df_inicial.to_csv(LOG_CSV, index=False)
                print(f"✅ Recreado {LOG_CSV} vacío")
                return
            
            # Intentar leer para verificar integridad
            try:
                df_test = pd.read_csv(LOG_CSV)
                if len(df_test.columns) == 0:
                    raise pd.errors.EmptyDataError("Sin columnas")
                print(f"✅ CSV verificado: {len(df_test)} registros")
            except (pd.errors.EmptyDataError, pd.errors.ParserError):
                # Archivo corrupto, recrear
                df_inicial = pd.DataFrame(columns=[
                    'timestamp', 'user_id', 'mensaje', 'respuesta', 'liga'
                ])
                df_inicial.to_csv(LOG_CSV, index=False)
                print(f"✅ CSV reconstruido por corrupción")
                
        except Exception as e:
            print(f"❌ Error inicializando CSV: {e}")

def registrar_interaccion(usuario, mensaje, respuesta, liga=None):
    """Registra una interacción de forma thread-safe"""
    try:
        # Asegurar que el CSV está inicializado
        inicializar_csv()
        
        timestamp = datetime.now().isoformat()
        
        # Limpiar datos para evitar problemas en CSV
        usuario_clean = str(usuario).replace(',', ';').replace('\n', ' ')[:50]
        mensaje_clean = str(mensaje).replace(',', ';').replace('\n', ' ')[:200]
        respuesta_clean = str(respuesta).replace(',', ';').replace('\n', ' ')[:500]
        liga_clean = str(liga) if liga else ""
        
        data = {
            "timestamp": timestamp,
            "user_id": usuario_clean,
            "mensaje": mensaje_clean,
            "respuesta": respuesta_clean,
            "liga": liga_clean
        }
        
        with log_lock:
            try:
                # Leer CSV existente de forma segura
                if os.path.exists(LOG_CSV) and os.path.getsize(LOG_CSV) > 0:
                    df = pd.read_csv(LOG_CSV)
                else:
                    df = pd.DataFrame(columns=['timestamp', 'user_id', 'mensaje', 'respuesta', 'liga'])
                
                # Agregar nueva fila
                new_row = pd.DataFrame([data])
                df = pd.concat([df, new_row], ignore_index=True)
                
                # Mantener solo los últimos 1000 registros
                if len(df) > 1000:
                    df = df.tail(1000)
                
                # Guardar CSV
                df.to_csv(LOG_CSV, index=False)
                
                # También guardar en JSON como backup
                with open(LOG_JSON, "a", encoding="utf-8") as f:
                    f.write(json.dumps(data, ensure_ascii=False) + "\n")
                
                print(f"📝 ✅ Interacción registrada: {usuario_clean} - {mensaje_clean[:30]}...")
                
            except Exception as e:
                print(f"❌ Error guardando en CSV: {e}")
                # Fallback: solo guardar en JSON
                with open(LOG_JSON, "a", encoding="utf-8") as f:
                    f.write(json.dumps(data, ensure_ascii=False) + "\n")
                print("📝 ⚠️ Guardado solo en JSON como fallback")
                
    except Exception as e:
        print(f"❌ Error crítico en logging: {e}")

def crear_datos_prueba():
    """Crea datos de prueba para el dashboard"""
    print("🔄 Creando datos de prueba...")
    
    # Datos de ejemplo
    datos_prueba = [
        {
            "timestamp": "2024-05-23 10:30:00",
            "user_id": "usuario1", 
            "mensaje": "Real Madrid próximos partidos",
            "respuesta": "Análisis del Real Madrid...",
            "liga": "PD"
        },
        {
            "timestamp": "2024-05-23 10:31:00",
            "user_id": "usuario2",
            "mensaje": "hola",
            "respuesta": "¡Hola! Soy tu bot de fútbol personalizado...",
            "liga": "personalizada"
        },
        {
            "timestamp": "2024-05-23 11:15:00",
            "user_id": "usuario1",
            "mensaje": "Barcelona análisis",
            "respuesta": "Análisis del FC Barcelona...",
            "liga": "PD"
        },
        {
            "timestamp": "2024-05-23 14:22:00",
            "user_id": "usuario3",
            "mensaje": "Manchester City vs Liverpool",
            "respuesta": "Predicción del partido...",
            "liga": "PL"
        },
        {
            "timestamp": "2024-05-23 16:45:00",
            "user_id": "usuario2",
            "mensaje": "Juventus forma reciente",
            "respuesta": "Análisis de la Juventus...",
            "liga": "SA"
        },
        {
            "timestamp": "2024-05-23 17:30:00",
            "user_id": "usuario4",
            "mensaje": "como estas",
            "respuesta": "¡Muy bien! Listo para analizar fútbol...",
            "liga": "personalizada"
        },
        {
            "timestamp": "2024-05-23 18:15:00",
            "user_id": "usuario1",
            "mensaje": "PSG próximos partidos",
            "respuesta": "Análisis del PSG...",
            "liga": "FL1"
        }
    ]


    
    
    # Crear DataFrame y guardar
    df = pd.DataFrame(datos_prueba)
    
    with log_lock:
        df.to_csv(LOG_CSV, index=False)
    
    print(f"✅ Creados {len(datos_prueba)} registros de prueba en {LOG_CSV}")
    print("🎉 ¡Ahora puedes ver métricas en el dashboard!")

def verificar_logs():
    """Verifica el estado de los archivos de log"""
    print("🔍 Verificando archivos de log...")
    
    # Verificar CSV
    if os.path.exists(LOG_CSV):
        try:
            df = pd.read_csv(LOG_CSV)
            print(f"✅ CSV: {len(df)} registros, columnas: {list(df.columns)}")
        except Exception as e:
            print(f"❌ Error en CSV: {e}")
    else:
        print("❌ CSV no existe")
    
    # Verificar JSON
    if os.path.exists(LOG_JSON):
        print(f"✅ JSON existe: {os.path.getsize(LOG_JSON)} bytes")
    else:
        print("❌ JSON no existe")
    
    # Verificar otros archivos
    archivos_sistema = [
        "logs/system_status.json",
        "logs/performance.json"
    ]
    
    for archivo in archivos_sistema:
        if os.path.exists(archivo):
            print(f"✅ {archivo} existe")
        else:
            print(f"❌ {archivo} no existe")

def test_logging():
    """Función para probar el sistema de logging"""
    print("🧪 Probando sistema de logging...")
    
    # Crear algunos registros de prueba
    registrar_interaccion("test_user1", "Real Madrid próximos partidos", "Análisis del Real Madrid...", "PD")
    registrar_interaccion("test_user2", "hola", "¡Hola! Soy tu bot...", "personalizada")
    registrar_interaccion("test_user1", "Barcelona vs Madrid", "Predicción del clásico...", "PD")
    
    # Verificar que se guardaron
    if os.path.exists(LOG_CSV):
        df = pd.read_csv(LOG_CSV)
        print(f"✅ Logging funcionando: {len(df)} registros en CSV")
    else:
        print("❌ Error: CSV no creado")

# Auto-inicializar al importar
inicializar_csv()

# SCRIPT PARA EJECUTAR MANUALMENTE
if __name__ == "__main__":
    print("🚀 Inicializando sistema de logs...")
    verificar_logs()
    print("\n" + "="*50)
    crear_datos_prueba()
    print("\n" + "="*50)
    verificar_logs()
    print("\n" + "="*50)
    test_logging()
    print("\n" + "="*50)
    verificar_logs()