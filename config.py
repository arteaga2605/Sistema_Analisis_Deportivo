# config.py
import os

# Capital inicial de la empresa (en unidades monetarias)
CAPITAL_INICIAL = 10.0

# Umbral de probabilidad mínima para considerar una predicción (65%)
UMBRAL_PROBABILIDAD = 0.65

# Número de fallos consecutivos que activan la alerta del gestor de riesgo
LIMITE_RACHA_FALLOS = 5

# Archivo donde se almacena el estado persistente
ARCHIVO_ESTADO = os.path.join(os.path.dirname(__file__), 'estado.json')

# Configuración de la API de MLB (original)
MLB_BASE_URL = 'https://statsapi.mlb.com/api/v1'
MLB_SPORT_ID = 1

# Porcentaje del capital a invertir (total a repartir entre predicciones del día)
PORCENTAJE_INVERSION_NORMAL = 0.05   # 5%
PORCENTAJE_INVERSION_RACHA = 0.01    # 1%

# Días hacia atrás para obtener récord reciente
DIAS_HISTORICO_RECIENTE = 14

# Configuración del sistema multi-proveedor
USE_MULTI_PROVIDER = True
ENABLE_SPORTS_SKILLS = True

# API Key de balldontlie.io (NBA)
BALDONTLIE_API_KEY = "b0a0657e-9de3-421f-aba5-381e3befef8e"

# BBC Sport scraping
ENABLE_BBC_SPORT = False
BBC_HEADLESS = True          # Ejecutar navegador sin interfaz gráfica
BBC_TIMEOUT = 30             # Tiempo máximo de espera para cargar la página

# Añadir al final del archivo config.py

# Estrategia de Kelly
KELLY_FRACTION = 0.25      # 25% del Kelly completo (conservador)
MIN_BET_SIZE = 0.10        # Monto mínimo a apostar (unidades)
MAX_BET_SIZE = 5.00        # Monto máximo a apostar (unidades)

# Para el creador de tickets, permitir selección interactiva
TICKET_SELECCION_INTERACTIVA = True   # True = preguntar por consola

# Configuración para sentimiento real de redes sociales
ENABLE_SOCIAL_SENTIMENT = True  # Activar análisis real con Xpoz + VADER
XPOZ_TOKEN = "K3BYC00RUorb213lokkDwORYimFtLbgWqw7lpbI5MOGdzCpjBGmnUFuP4skBKu6GMuuVhu9"  # Token personal de Xpoz (obtener en https://xpoz.ai)