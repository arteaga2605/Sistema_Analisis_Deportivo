# analista_excel.py
"""
Analista híbrido que obtiene estadísticas de equipos desde archivos locales (MLB y NBA)
y los juegos del día desde APIs online (con fallback a archivo local).
"""

import pandas as pd
import numpy as np
from datetime import date, datetime
from typing import List, Dict, Any, Optional
import os
import re
import unicodedata

from models import Prediccion
from config import UMBRAL_PROBABILIDAD, USE_MULTI_PROVIDER

# Importar DataProviderManager si está activado
if USE_MULTI_PROVIDER:
    from data_providers import DataProviderManager
    data_manager = DataProviderManager()

# ------------------------------------------------------------
# Mapeo de nombres de equipos en inglés a español (MLB)
# ------------------------------------------------------------
NOMBRES_INGLES_A_ESPANOL_MLB = {
    "Arizona Diamondbacks": "Diamondbacks de Arizona",
    "Arizona D'Backs": "Diamondbacks de Arizona",
    "Atlanta Braves": "Bravos de Atlanta",
    "Baltimore Orioles": "Orioles de Baltimore",
    "Boston Red Sox": "Medias Rojas de Boston",
    "Chicago White Sox": "Medias Blancas de Chicago",
    "Chicago Cubs": "Cachorros de Chicago",
    "Cincinnati Reds": "Rojos de Cincinnati",
    "Cleveland Guardians": "Guardianes de Cleveland",
    "Colorado Rockies": "Montañas Rocosas de Colorado",
    "Detroit Tigers": "Tigres de Detroit",
    "Houston Astros": "Astros de Houston",
    "Kansas City Royals": "Reales de Kansas City",
    "Los Angeles Angels": "Los Ángeles Angels",
    "Los Angeles Dodgers": "Dodgers de Los Ángeles",
    "Miami Marlins": "Marlins de Miami",
    "Milwaukee Brewers": "Cerveceros de Milwaukee",
    "Minnesota Twins": "Minnesota Twins",
    "New York Yankees": "Yankees de Nueva York",
    "New York Mets": "Mets de Nueva York",
    "Oakland Athletics": "Atletismo",
    "Athletics": "Atletismo",
    "Philadelphia Phillies": "Filis de Filadelfia",
    "Pittsburgh Pirates": "Piratas de Pittsburgh",
    "San Diego Padres": "Padres de San Diego",
    "San Francisco Giants": "Gigantes de San Francisco",
    "Seattle Mariners": "Marineros de Seattle",
    "St. Louis Cardinals": "Cardenales de San Luis",
    "Tampa Bay Rays": "Rayos de Tampa Bay",
    "Texas Rangers": "Rangers de Texas",
    "Toronto Blue Jays": "Azulejos de Toronto",
    "Washington Nationals": "Nacionales de Washington"
}

def normalizar_nombre(nombre: str) -> str:
    """Elimina acentos, caracteres especiales y convierte a minúsculas."""
    nombre = nombre.lower().strip()
    nombre = re.sub(r'[^a-záéíóúñü ]', '', nombre)
    nombre = ''.join(c for c in unicodedata.normalize('NFD', nombre)
                     if unicodedata.category(c) != 'Mn')
    return nombre

def encontrar_columna(df, posibles):
    """Busca una columna cuyo nombre contenga alguna de las cadenas posibles."""
    for col in df.columns:
        col_str = str(col).strip()
        for p in posibles:
            if p in col_str.upper():
                return col
    return None

def limpiar_valor(val):
    """Convierte un valor a float si es posible, manejando comas y porcentajes."""
    if pd.isna(val):
        return None
    if isinstance(val, str):
        val = val.replace(',', '.').replace('%', '')
        val = re.sub(r'[^0-9.-]', '', val)
        try:
            return float(val) if val else None
        except:
            return None
    try:
        return float(val)
    except:
        return None

class AnalistaExcel:
    def __init__(self, carpeta_datos="."):
        self.nombre = "Analista Excel"
        self.carpeta = carpeta_datos
        # Cargar estadísticas desde archivos locales (siempre)
        self.mlb_stats = self._cargar_mlb_stats()
        self.nba_stats = self._cargar_nba_stats()
        # Cargar archivo local como fallback
        self.schedule_local = self._cargar_schedule_local()

    # -------------------------------------------------------------------
    # Lectura de archivos Excel (reemplaza la anterior lectura HTML)
    # -------------------------------------------------------------------
    def _leer_tabla_excel(self, ruta):
        """Lee un archivo Excel y devuelve un DataFrame con limpieza básica."""
        try:
            df = pd.read_excel(ruta, engine='openpyxl')
            # Convertir posibles columnas numéricas que vengan como texto con comas
            for col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                    df[col] = pd.to_numeric(df[col], errors='ignore')
            return df
        except Exception as e:
            print(f"Error leyendo {ruta}: {e}")
            return None

    # -------------------------------------------------------------------
    # Carga de estadísticas de MLB (archivos locales Excel)
    # -------------------------------------------------------------------
    def _cargar_mlb_stats(self) -> Dict[str, Dict]:
        archivo_bateo = None
        archivo_pitcheo = None
        for f in os.listdir(self.carpeta):
            if f.startswith("sportsref_download") and f.endswith(".xls"):
                if "(1)" in f:
                    archivo_pitcheo = os.path.join(self.carpeta, f)
                else:
                    archivo_bateo = os.path.join(self.carpeta, f)

        if not archivo_bateo or not archivo_pitcheo:
            print("⚠️ No se encontraron los dos archivos de MLB (bateo y pitcheo).")
            return {}

        df_bateo = self._leer_tabla_excel(archivo_bateo)
        df_pitcheo = self._leer_tabla_excel(archivo_pitcheo)

        if df_bateo is None or df_pitcheo is None:
            return {}

        df_bateo.columns = [str(col).strip() for col in df_bateo.columns]
        df_pitcheo.columns = [str(col).strip() for col in df_pitcheo.columns]

        # Mostrar nombres de columnas para depuración (solo la primera vez)
        if not hasattr(self, '_columnas_mostradas'):
            print("\n🔍 Columnas en tabla de bateo:", list(df_bateo.columns))
            print("🔍 Columnas en tabla de pitcheo:", list(df_pitcheo.columns))
            self._columnas_mostradas = True

        # Identificar columna de equipo
        col_team_b = encontrar_columna(df_bateo, ["Tm", "Team"])
        if not col_team_b:
            col_team_b = df_bateo.columns[0]
        col_team_p = encontrar_columna(df_pitcheo, ["Tm", "Team"])
        if not col_team_p:
            col_team_p = df_pitcheo.columns[0]

        # Nombres exactos de columnas según la estructura de los archivos
        # Bateo
        col_avg = 'licenciado en Letras'  # AVG
        col_obp = 'OBP'
        col_slg = 'SLG'
        col_ops = 'Operaciones'
        col_ops_plus = 'OPS+'
        col_tb = 'tuberculosis'
        col_gdp = 'PIB'
        col_hbp = 'HBP'
        col_sb = 'SB'
        col_cs = 'CS'
        col_bb = 'CAMA Y DESAYUNO'
        col_so = 'ENTONCES'

        # Pitcheo
        col_era = 'TRAPO'          # ERA
        col_cg = 'CG'
        col_defeff = 'Defensa'     # DefEff
        col_fld = 'Fld%'
        col_rtot = 'Rtot'
        col_rdrs = 'Carreteras'    # Rdrs
        col_rgood = 'Rgood'

        # Crear diccionario base con equipos de bateo
        stats = {}
        for _, row in df_bateo.iterrows():
            team = str(row[col_team_b]).strip()
            if team in ["Promedio de la liga", "Total", "League Average", ""] or not team:
                continue
            stats[team] = {}

        # Procesar bateo
        for _, row in df_bateo.iterrows():
            team = str(row[col_team_b]).strip()
            if team not in stats:
                continue
            stats[team]['bateo'] = {}
            stats[team]['bateo']['AVG'] = limpiar_valor(row[col_avg]) if col_avg in df_bateo.columns else None
            stats[team]['bateo']['OBP'] = limpiar_valor(row[col_obp]) if col_obp in df_bateo.columns else None
            stats[team]['bateo']['SLG'] = limpiar_valor(row[col_slg]) if col_slg in df_bateo.columns else None
            stats[team]['bateo']['OPS'] = limpiar_valor(row[col_ops]) if col_ops in df_bateo.columns else None
            stats[team]['bateo']['OPS+'] = limpiar_valor(row[col_ops_plus]) if col_ops_plus in df_bateo.columns else None
            stats[team]['bateo']['TB'] = limpiar_valor(row[col_tb]) if col_tb in df_bateo.columns else None
            stats[team]['bateo']['GDP'] = limpiar_valor(row[col_gdp]) if col_gdp in df_bateo.columns else None
            stats[team]['bateo']['HBP'] = limpiar_valor(row[col_hbp]) if col_hbp in df_bateo.columns else None
            stats[team]['bateo']['SB'] = limpiar_valor(row[col_sb]) if col_sb in df_bateo.columns else None
            stats[team]['bateo']['CS'] = limpiar_valor(row[col_cs]) if col_cs in df_bateo.columns else None
            stats[team]['bateo']['BB'] = limpiar_valor(row[col_bb]) if col_bb in df_bateo.columns else None
            stats[team]['bateo']['SO'] = limpiar_valor(row[col_so]) if col_so in df_bateo.columns else None

        # Procesar pitcheo
        for _, row in df_pitcheo.iterrows():
            team = str(row[col_team_p]).strip()
            if team not in stats:
                continue
            stats[team]['pitcheo'] = {}
            era_val = limpiar_valor(row[col_era]) if col_era in df_pitcheo.columns else None
            # Si el valor es negativo, tomar absoluto (puede ser ERA+ o un error)
            if era_val is not None and era_val < 0:
                era_val = abs(era_val)
            stats[team]['pitcheo']['ERA'] = era_val
            stats[team]['pitcheo']['CG'] = limpiar_valor(row[col_cg]) if col_cg in df_pitcheo.columns else None

            stats[team]['defensa'] = {}
            stats[team]['defensa']['DefEff'] = limpiar_valor(row[col_defeff]) if col_defeff in df_pitcheo.columns else None
            stats[team]['defensa']['Fld%'] = limpiar_valor(row[col_fld]) if col_fld in df_pitcheo.columns else None
            stats[team]['defensa']['Rtot'] = limpiar_valor(row[col_rtot]) if col_rtot in df_pitcheo.columns else None
            stats[team]['defensa']['Rdrs'] = limpiar_valor(row[col_rdrs]) if col_rdrs in df_pitcheo.columns else None
            stats[team]['defensa']['Rgood'] = limpiar_valor(row[col_rgood]) if col_rgood in df_pitcheo.columns else None

        # Mostrar resumen
        print(f"✓ Cargadas estadísticas completas de MLB para {len(stats)} equipos.")
        if stats:
            print(f"  Ejemplos MLB: {list(stats.keys())[:5]}")
        return stats

    # -------------------------------------------------------------------
    # Carga de estadísticas de NBA (archivos locales HTML)
    # -------------------------------------------------------------------
    def _cargar_nba_stats(self) -> Dict[str, Dict]:
        archivo = os.path.join(self.carpeta, "nba_stats.html")
        if not os.path.exists(archivo):
            print("⚠️ No se encontró nba_stats.html. La NBA no estará disponible.")
            return {}

        try:
            tablas = pd.read_html(archivo, flavor='html5lib')
            if not tablas:
                print("⚠️ No se encontraron tablas en nba_stats.html")
                return {}

            df = None
            for idx, tbl in enumerate(tablas):
                tbl.columns = [str(col).strip() for col in tbl.columns]
                if 'Team' in tbl.columns:
                    if any(col in tbl.columns for col in ['Pace', 'OffRtg', 'PTS', 'eFG%']):
                        df = tbl
                        print(f"  Tabla {idx} seleccionada para NBA")
                        # Mostrar columnas para depuración
                        print(f"  Columnas NBA: {list(df.columns)}")
                        break

            if df is None:
                print("⚠️ No se encontró la tabla de estadísticas de equipos en nba_stats.html")
                return {}

            col_team = 'Team'
            stats = {}
            for _, row in df.iterrows():
                team = str(row[col_team]).strip()
                if team in ["League Average", "Total", ""] or not team:
                    continue
                stats[team] = {}
                if 'Pace' in df.columns:
                    stats[team]['Pace'] = limpiar_valor(row['Pace'])
                if 'OffRtg' in df.columns:
                    stats[team]['OffRtg'] = limpiar_valor(row['OffRtg'])
                if 'DefRtg' in df.columns:
                    stats[team]['DefRtg'] = limpiar_valor(row['DefRtg'])
                if 'eFG%' in df.columns:
                    stats[team]['eFG%'] = limpiar_valor(row['eFG%'])
                if 'TS%' in df.columns:
                    stats[team]['TS%'] = limpiar_valor(row['TS%'])
                if 'ORB%' in df.columns:
                    stats[team]['ORB%'] = limpiar_valor(row['ORB%'])
                if 'DRB%' in df.columns:
                    stats[team]['DRB%'] = limpiar_valor(row['DRB%'])
                if 'TOV%' in df.columns:
                    stats[team]['TOV%'] = limpiar_valor(row['TOV%'])
                if 'PTS' in df.columns:
                    stats[team]['PTS'] = limpiar_valor(row['PTS'])

            print(f"✓ Cargadas estadísticas de NBA para {len(stats)} equipos.")
            if stats:
                print(f"  Ejemplos NBA: {list(stats.keys())[:5]}")
            return stats

        except Exception as e:
            print(f"Error cargando NBA: {e}")
            return {}

    # -------------------------------------------------------------------
    # Carga de calendario local (fallback)
    # -------------------------------------------------------------------
    def _cargar_schedule_local(self) -> pd.DataFrame:
        posibles = ["schedule.xlsx", "schedule.csv"]
        archivo = None
        for p in posibles:
            ruta = os.path.join(self.carpeta, p)
            if os.path.exists(ruta):
                archivo = ruta
                break
        if archivo is None:
            return pd.DataFrame()
        try:
            if archivo.endswith('.csv'):
                df = pd.read_csv(archivo)
            else:
                df = pd.read_excel(archivo)
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
            df = df.dropna(subset=['fecha'])
            print(f"✓ Calendario local cargado: {len(df)} partidos (fallback).")
            return df
        except Exception as e:
            print(f"Error cargando schedule local: {e}")
            return pd.DataFrame()

    # -------------------------------------------------------------------
    # Obtener juegos del día (online + fallback)
    # -------------------------------------------------------------------
    def _obtener_juegos_dia(self, fecha: date) -> List[Dict[str, Any]]:
        """Obtiene juegos del día desde APIs online (MLB, NBA). Si falla, usa archivo local."""
        juegos = []

        # Intentar con DataProviderManager
        if USE_MULTI_PROVIDER:
            try:
                print("Obteniendo juegos del día desde APIs online...")
                juegos_raw = data_manager.get_games_by_date(fecha)
                for j in juegos_raw:
                    # Filtrar solo MLB y NBA
                    sport = j.get('sport', '').lower()
                    if sport in ['mlb', 'nba', 'basketball']:
                        # Determinar el deporte
                        if sport == 'mlb':
                            deporte = 'mlb'
                        else:
                            deporte = 'nba'
                        home = j.get('home_team', '')
                        away = j.get('away_team', '')
                        if home and away:
                            juegos.append({
                                'deporte': deporte,
                                'local': home,
                                'visitante': away,
                                'fecha': fecha
                            })
                if juegos:
                    print(f"✓ Se obtuvieron {len(juegos)} partidos online para hoy.")
                    return juegos
                else:
                    print("⚠️ No se obtuvieron partidos online.")
            except Exception as e:
                print(f"⚠️ Error obteniendo juegos online: {e}")

        # Fallback: usar archivo local
        print("Usando archivo local como fallback...")
        if not self.schedule_local.empty:
            fecha_dt = pd.to_datetime(fecha)
            df_hoy = self.schedule_local[self.schedule_local['fecha'].dt.date == fecha_dt.date()]
            for _, row in df_hoy.iterrows():
                deporte = row.get('deporte', 'mlb').lower()
                if deporte not in ['mlb', 'nba']:
                    continue
                juegos.append({
                    'deporte': deporte,
                    'local': row['equipo_local'],
                    'visitante': row['equipo_visitante'],
                    'fecha': fecha
                })
            if juegos:
                print(f"✓ Se obtuvieron {len(juegos)} partidos del archivo local.")
                return juegos

        print("No se encontraron partidos para hoy.")
        return []

    # -------------------------------------------------------------------
    # Obtener métricas de un equipo de MLB (con mapeo inglés->español)
    # -------------------------------------------------------------------
    def _obtener_metricas_mlb(self, nombre_equipo: str) -> Dict[str, Dict]:
        nombre_es = NOMBRES_INGLES_A_ESPANOL_MLB.get(nombre_equipo, nombre_equipo)
        norm_busqueda = normalizar_nombre(nombre_es)
        for k in self.mlb_stats:
            if normalizar_nombre(k) == norm_busqueda:
                return self.mlb_stats[k]
            if norm_busqueda in normalizar_nombre(k) or normalizar_nombre(k) in norm_busqueda:
                return self.mlb_stats[k]
        print(f"  ⚠️ Equipo MLB '{nombre_equipo}' no encontrado.")
        return {}

    # -------------------------------------------------------------------
    # Obtener métricas de un equipo de NBA (con alias y limpieza)
    # -------------------------------------------------------------------
    def _obtener_metricas_nba(self, nombre_equipo: str) -> Dict[str, float]:
        # Mapeo de alias comunes (para nombres abreviados)
        alias = {
            "LA Lakers": "Los Angeles Lakers",
            "Lakers": "Los Angeles Lakers",
            "Golden State": "Golden State Warriors",
            "Warriors": "Golden State Warriors",
            "OKC": "Oklahoma City Thunder",
            "Thunder": "Oklahoma City Thunder",
            "Portland": "Portland Trail Blazers",
            "New Orleans": "New Orleans Pelicans",
            "Sacramento": "Sacramento Kings",
            "Minnesota": "Minnesota Timberwolves",
            "Memphis": "Memphis Grizzlies",
            "Utah": "Utah Jazz",
            "Denver": "Denver Nuggets",
            "Dallas": "Dallas Mavericks",
            "Houston": "Houston Rockets",
            "Phoenix": "Phoenix Suns",
            "San Antonio": "San Antonio Spurs",
            "Miami": "Miami Heat",
            "Boston": "Boston Celtics",
            "Brooklyn": "Brooklyn Nets",
            "New York": "New York Knicks",
            "Philadelphia": "Philadelphia 76ers",
            "Toronto": "Toronto Raptors",
            "Chicago": "Chicago Bulls",
            "Cleveland": "Cleveland Cavaliers",
            "Detroit": "Detroit Pistons",
            "Indiana": "Indiana Pacers",
            "Milwaukee": "Milwaukee Bucks",
            "Atlanta": "Atlanta Hawks",
            "Charlotte": "Charlotte Hornets",
            "Orlando": "Orlando Magic",
            "Washington": "Washington Wizards"
        }
        # Primero intentamos con el nombre original (puede venir ya completo)
        nombre_original = nombre_equipo.replace('*', '').strip()
        norm_busqueda = normalizar_nombre(nombre_original)
        for k in self.nba_stats:
            k_limpio = k.replace('*', '').strip()
            if normalizar_nombre(k_limpio) == norm_busqueda:
                return self.nba_stats[k]
            if norm_busqueda in normalizar_nombre(k_limpio) or normalizar_nombre(k_limpio) in norm_busqueda:
                return self.nba_stats[k]

        # Si no se encuentra, probamos con alias
        nombre_aliased = alias.get(nombre_original, nombre_original)
        if nombre_aliased != nombre_original:
            norm_busqueda = normalizar_nombre(nombre_aliased)
            for k in self.nba_stats:
                k_limpio = k.replace('*', '').strip()
                if normalizar_nombre(k_limpio) == norm_busqueda:
                    return self.nba_stats[k]
                if norm_busqueda in normalizar_nombre(k_limpio) or normalizar_nombre(k_limpio) in norm_busqueda:
                    return self.nba_stats[k]

        print(f"  ⚠️ Equipo NBA '{nombre_equipo}' no encontrado.")
        return {}

    # -------------------------------------------------------------------
    # Modelos de probabilidad (ajustados para mayor sensibilidad)
    # -------------------------------------------------------------------
    def _calcular_probabilidad_mlb(self, local: Dict, visitante: Dict) -> float:
        """Calcula probabilidad para MLB usando todas las métricas disponibles."""
        def norm(value, is_lower_better=False, max_val=1.0):
            if value is None:
                return 0.5
            if is_lower_better:
                if value <= 0:
                    return 1.0
                if value > max_val * 2:
                    return 0.0
                return max(0, min(1, (max_val - value) / max_val))
            else:
                if value <= 0:
                    return 0.0
                if value > max_val * 2:
                    return 1.0
                return max(0, min(1, value / max_val))

        bateo_l = local.get('bateo', {})
        bateo_v = visitante.get('bateo', {})
        avg = norm(bateo_l.get('AVG'), max_val=0.35) - norm(bateo_v.get('AVG'), max_val=0.35)
        obp = norm(bateo_l.get('OBP'), max_val=0.45) - norm(bateo_v.get('OBP'), max_val=0.45)
        slg = norm(bateo_l.get('SLG'), max_val=0.7) - norm(bateo_v.get('SLG'), max_val=0.7)
        ops = norm(bateo_l.get('OPS'), max_val=1.0) - norm(bateo_v.get('OPS'), max_val=1.0)
        ops_plus = norm(bateo_l.get('OPS+'), max_val=200) - norm(bateo_v.get('OPS+'), max_val=200)
        tb = norm(bateo_l.get('TB'), max_val=60) - norm(bateo_v.get('TB'), max_val=60)
        sb = norm(bateo_l.get('SB'), max_val=30) - norm(bateo_v.get('SB'), max_val=30)
        bb = norm(bateo_l.get('BB'), max_val=50) - norm(bateo_v.get('BB'), max_val=50)
        gdp_l = norm(bateo_l.get('GDP'), is_lower_better=True, max_val=10)
        gdp_v = norm(bateo_v.get('GDP'), is_lower_better=True, max_val=10)
        gdp_adv = gdp_l - gdp_v
        cs_l = norm(bateo_l.get('CS'), is_lower_better=True, max_val=10)
        cs_v = norm(bateo_v.get('CS'), is_lower_better=True, max_val=10)
        cs_adv = cs_l - cs_v
        so_l = norm(bateo_l.get('SO'), is_lower_better=True, max_val=100)
        so_v = norm(bateo_v.get('SO'), is_lower_better=True, max_val=100)
        so_adv = so_l - so_v
        ofensa_adv = (avg + obp + slg + ops + ops_plus + tb + sb + bb + gdp_adv + cs_adv + so_adv) / 11.0

        pitcheo_l = local.get('pitcheo', {})
        pitcheo_v = visitante.get('pitcheo', {})
        era = norm(pitcheo_l.get('ERA'), is_lower_better=True, max_val=5.0) - norm(pitcheo_v.get('ERA'), is_lower_better=True, max_val=5.0)
        pitcheo_adv = era  # simplificado

        defensa_l = local.get('defensa', {})
        defensa_v = visitante.get('defensa', {})
        defeff = norm(defensa_l.get('DefEff'), max_val=1.0) - norm(defensa_v.get('DefEff'), max_val=1.0)
        fld = norm(defensa_l.get('Fld%'), max_val=1.0) - norm(defensa_v.get('Fld%'), max_val=1.0)
        def norm_r(val):
            if val is None:
                return 0
            return max(-1, min(1, val / 20))
        rtot = norm_r(defensa_l.get('Rtot')) - norm_r(defensa_v.get('Rtot'))
        rdrs = norm_r(defensa_l.get('Rdrs')) - norm_r(defensa_v.get('Rdrs'))
        rgood = norm_r(defensa_l.get('Rgood')) - norm_r(defensa_v.get('Rgood'))
        defensa_adv = (defeff + fld + rtot + rdrs + rgood) / 5.0

        score_local = ofensa_adv * 0.30 + pitcheo_adv * 0.40 + defensa_adv * 0.30
        prob_local = 0.5 + score_local * 0.5  # aumentado de 0.3 a 0.5 para mayor sensibilidad
        return max(0.05, min(0.95, prob_local))

    def _calcular_probabilidad_nba(self, local: Dict, visitante: Dict) -> float:
        """Calcula probabilidad para NBA usando métricas clave."""
        def norm(value, is_lower_better=False, max_val=1.0):
            if value is None:
                return 0.5
            if is_lower_better:
                if value <= 0:
                    return 1.0
                if value > max_val * 2:
                    return 0.0
                return max(0, min(1, (max_val - value) / max_val))
            else:
                if value <= 0:
                    return 0.0
                if value > max_val * 2:
                    return 1.0
                return max(0, min(1, value / max_val))

        off_local = norm(local.get('OffRtg'), max_val=120)
        off_visit = norm(visitante.get('OffRtg'), max_val=120)
        off_adv = off_local - off_visit

        def_local = norm(local.get('DefRtg'), is_lower_better=True, max_val=120)
        def_visit = norm(visitante.get('DefRtg'), is_lower_better=True, max_val=120)
        def_adv = def_local - def_visit

        efg_local = norm(local.get('eFG%'), max_val=0.55)
        efg_visit = norm(visitante.get('eFG%'), max_val=0.55)
        efg_adv = efg_local - efg_visit

        ts_local = norm(local.get('TS%'), max_val=0.58)
        ts_visit = norm(visitante.get('TS%'), max_val=0.58)
        ts_adv = ts_local - ts_visit

        orb_local = norm(local.get('ORB%'), max_val=30)
        orb_visit = norm(visitante.get('ORB%'), max_val=30)
        orb_adv = orb_local - orb_visit
        drb_local = norm(local.get('DRB%'), max_val=80)
        drb_visit = norm(visitante.get('DRB%'), max_val=80)
        drb_adv = drb_local - drb_visit

        tov_local = norm(local.get('TOV%'), is_lower_better=True, max_val=15)
        tov_visit = norm(visitante.get('TOV%'), is_lower_better=True, max_val=15)
        tov_adv = tov_local - tov_visit

        score_local = (off_adv * 0.25 +
                       def_adv * 0.25 +
                       efg_adv * 0.10 +
                       ts_adv * 0.10 +
                       orb_adv * 0.10 +
                       drb_adv * 0.10 +
                       tov_adv * 0.10)
        prob_local = 0.5 + score_local * 0.5  # aumentado para mayor sensibilidad
        return max(0.05, min(0.95, prob_local))

    # -------------------------------------------------------------------
    # Método principal
    # -------------------------------------------------------------------
    def analizar_juegos_dia(self, fecha: date) -> List[Prediccion]:
        juegos = self._obtener_juegos_dia(fecha)
        if not juegos:
            return []

        predicciones = []
        for juego in juegos:
            deporte = juego['deporte']
            local = juego['local']
            visitante = juego['visitante']

            if deporte == 'mlb':
                stats_local = self._obtener_metricas_mlb(local)
                stats_visit = self._obtener_metricas_mlb(visitante)
                if not stats_local or not stats_visit:
                    continue
                prob_local = self._calcular_probabilidad_mlb(stats_local, stats_visit)
                ganador = local if prob_local > 0.5 else visitante
                prob = max(prob_local, 1 - prob_local)
                if prob < UMBRAL_PROBABILIDAD:
                    print(f"  DEBUG: {local} vs {visitante} → prob = {prob:.2%} (no supera umbral)")
                    continue
                comentario = (f"MLB: AVG ({stats_local.get('bateo',{}).get('AVG','N/A')} vs {stats_visit.get('bateo',{}).get('AVG','N/A')}), "
                              f"ERA ({stats_local.get('pitcheo',{}).get('ERA','N/A')} vs {stats_visit.get('pitcheo',{}).get('ERA','N/A')})")
            elif deporte == 'nba':
                stats_local = self._obtener_metricas_nba(local)
                stats_visit = self._obtener_metricas_nba(visitante)
                if not stats_local or not stats_visit:
                    continue
                prob_local = self._calcular_probabilidad_nba(stats_local, stats_visit)
                ganador = local if prob_local > 0.5 else visitante
                prob = max(prob_local, 1 - prob_local)
                if prob < UMBRAL_PROBABILIDAD:
                    print(f"  DEBUG: {local} vs {visitante} → prob = {prob:.2%} (no supera umbral)")
                    continue
                comentario = (f"NBA: OffRtg ({stats_local.get('OffRtg','N/A')} vs {stats_visit.get('OffRtg','N/A')}), "
                              f"DefRtg ({stats_local.get('DefRtg','N/A')} vs {stats_visit.get('DefRtg','N/A')}), "
                              f"eFG% ({stats_local.get('eFG%','N/A')} vs {stats_visit.get('eFG%','N/A')})")
            else:
                continue

            pred = Prediccion(
                fecha=fecha,
                equipo_local=local,
                equipo_visitante=visitante,
                ganador_predicho=ganador,
                probabilidad=prob,
                deporte=deporte.upper(),
                comentario=comentario,
                analista=self.nombre
            )
            predicciones.append(pred)

        return predicciones