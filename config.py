# config.py
import os

# Capital inicial de la empresa (en Bolívares)
CAPITAL_INICIAL = 1000.0

# Umbral de probabilidad mínima para considerar una predicción (65%)
UMBRAL_PROBABILIDAD = 0.65

# Número de fallos consecutivos que activan la alerta del gestor de riesgo
LIMITE_RACHA_FALLOS = 5

# Archivo donde se almacena el estado persistente
ARCHIVO_ESTADO = os.path.join(os.path.dirname(__file__), 'estado.json')

# Configuración de la API de MLB (original – se mantiene por compatibilidad)
MLB_BASE_URL = 'https://statsapi.mlb.com/api/v1'
MLB_SPORT_ID = 1

# Porcentaje del capital a invertir (total a repartir entre predicciones del día)
PORCENTAJE_INVERSION_NORMAL = 0.05   # 5%
PORCENTAJE_INVERSION_RACHA = 0.01    # 1%

# Días hacia atrás para obtener récord reciente (no se usa en la nueva versión)
DIAS_HISTORICO_RECIENTE = 14

# Configuración del sistema multi-proveedor (se mantiene)
USE_MULTI_PROVIDER = True
ENABLE_SPORTS_SKILLS = True

# API Key de balldontlie.io (NBA)
BALDONTLIE_API_KEY = "b0a0657e-9de3-421f-aba5-381e3befef8e"

# BBC Sport scraping (se puede desactivar)
ENABLE_BBC_SPORT = True
BBC_HEADLESS = True
BBC_TIMEOUT = 30

# Símbolo de moneda
MONEDA_SIMBOLO = "Bs"

# Configuración para sentimiento real de redes sociales (desactivado por defecto)
ENABLE_SOCIAL_SENTIMENT = False
XPOZ_TOKEN = "K3BYC00RUorb213lokkDwORYimFtLbgWqw7lpbI5MOGdzCpjBGmnUFuP4skBKu6GMuuVhu9"

# Scraping de Sports-Reference
SCRAPING_DELAY = 3          # segundos entre peticiones
USE_SCRAPING = True         # False = usar solo archivos locales
SCRAPE_GAMES = False        # True = obtener partidos por scraping, False = usar schedule.csv