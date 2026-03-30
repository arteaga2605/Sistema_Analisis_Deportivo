# analista_excel.py
"""
Analista offline que lee directamente los archivos descargados:
- sportsref_download.xls (bateo MLB)
- sportsref_download (1).xls (pitcheo MLB)
- E0.csv (Premier League)
- schedule.csv o schedule.xlsx (calendario de partidos)
"""

import pandas as pd
import numpy as np
from datetime import date, datetime
from typing import List, Dict, Any, Optional
import os
import re
import unicodedata

from models import Prediccion
from config import UMBRAL_PROBABILIDAD

# ------------------------------------------------------------
# Mapeo de nombres en inglés (calendario) a español (estadísticas MLB)
# ------------------------------------------------------------
NOMBRES_INGLES_A_ESPANOL = {
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
    """Elimina acentos y convierte a minúsculas, también elimina apóstrofes y espacios extras."""
    nombre = nombre.lower().strip()
    # Eliminar caracteres no alfanuméricos (excepto espacios) para mejorar coincidencia
    nombre = re.sub(r"[^a-záéíóúñü ]", "", nombre)
    # Eliminar acentos
    nombre = ''.join(c for c in unicodedata.normalize('NFD', nombre)
                     if unicodedata.category(c) != 'Mn')
    return nombre

class AnalistaExcel:
    def __init__(self, carpeta_datos="."):
        self.nombre = "Analista Excel"
        self.carpeta = carpeta_datos
        self.mlb_stats = self._cargar_mlb_stats()
        self.soccer_stats = self._cargar_soccer_stats()
        self.schedule = self._cargar_schedule()

    # -------------------------------------------------------------------
    # Carga de datos MLB (bateo + pitcheo)
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

        df_bateo = self._leer_tabla_html(archivo_bateo)
        df_pitcheo = self._leer_tabla_html(archivo_pitcheo)

        if df_bateo is None or df_pitcheo is None:
            return {}

        # Limpiar nombres de columnas
        df_bateo.columns = [str(col).strip() for col in df_bateo.columns]
        df_pitcheo.columns = [str(col).strip() for col in df_pitcheo.columns]

        # Identificar columnas
        col_team_b = self._encontrar_columna(df_bateo, ["Tm", "Team"])
        if not col_team_b:
            col_team_b = df_bateo.columns[0]

        col_avg = self._encontrar_columna(df_bateo, ["AVG", "BA"])
        col_obp = self._encontrar_columna(df_bateo, ["OBP"])
        col_slg = self._encontrar_columna(df_bateo, ["SLG"])

        col_team_p = self._encontrar_columna(df_pitcheo, ["Tm", "Team"])
        if not col_team_p:
            col_team_p = df_pitcheo.columns[0]
        col_trapo = self._encontrar_columna(df_pitcheo, ["TRAPO"])

        stats = {}

        # Procesar bateo
        for _, row in df_bateo.iterrows():
            team = str(row[col_team_b]).strip()
            if team in ["Promedio de la liga", "Total", ""] or not team:
                continue
            stats[team] = {}
            # AVG
            try:
                avg_val = row[col_avg] if col_avg else None
                if isinstance(avg_val, str):
                    avg_val = avg_val.replace(',', '.').replace('%', '')
                    avg_val = re.sub(r'[^0-9.-]', '', avg_val)
                    avg_val = float(avg_val) if avg_val else None
                else:
                    avg_val = float(avg_val) if avg_val is not None else None
                stats[team]['AVG'] = avg_val
            except:
                stats[team]['AVG'] = None

            # OBP
            try:
                obp_val = row[col_obp] if col_obp else None
                if isinstance(obp_val, str):
                    obp_val = obp_val.replace(',', '.').replace('%', '')
                    obp_val = re.sub(r'[^0-9.-]', '', obp_val)
                    obp_val = float(obp_val) if obp_val else None
                else:
                    obp_val = float(obp_val) if obp_val is not None else None
                stats[team]['OBP'] = obp_val
            except:
                stats[team]['OBP'] = None

            # SLG
            try:
                slg_val = row[col_slg] if col_slg else None
                if isinstance(slg_val, str):
                    slg_val = slg_val.replace(',', '.').replace('%', '')
                    slg_val = re.sub(r'[^0-9.-]', '', slg_val)
                    slg_val = float(slg_val) if slg_val else None
                else:
                    slg_val = float(slg_val) if slg_val is not None else None
                stats[team]['SLG'] = slg_val
            except:
                stats[team]['SLG'] = None

        # Procesar pitcheo
        for _, row in df_pitcheo.iterrows():
            team = str(row[col_team_p]).strip()
            if team in ["Promedio de la liga", "Total", ""] or not team:
                continue
            if team not in stats:
                stats[team] = {}
            try:
                trapo_val = row[col_trapo] if col_trapo else None
                if isinstance(trapo_val, str):
                    trapo_val = trapo_val.replace(',', '.').replace('%', '')
                    trapo_val = re.sub(r'[^0-9.-]', '', trapo_val)
                    trapo_val = float(trapo_val) if trapo_val else None
                else:
                    trapo_val = float(trapo_val) if trapo_val is not None else None
                stats[team]['TRAPO'] = trapo_val
            except:
                stats[team]['TRAPO'] = None

        # Mostrar equipos cargados (primeros 10)
        equipos_cargados = list(stats.keys())
        print(f"✓ Cargadas estadísticas de MLB para {len(equipos_cargados)} equipos.")
        if equipos_cargados:
            print(f"  Ejemplos: {equipos_cargados[:5]}")
        return stats

    def _leer_tabla_html(self, ruta):
        """Lee un archivo .xls que contiene una tabla HTML y devuelve un DataFrame."""
        try:
            df_list = pd.read_html(ruta, flavor='html5lib')
            if df_list:
                df = df_list[0]
                # Convertir valores con coma decimal a punto
                for col in df.columns:
                    if df[col].dtype == object:
                        df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                        df[col] = pd.to_numeric(df[col], errors='ignore')
                return df
            else:
                print(f"⚠️ No se encontraron tablas en {ruta}")
                return None
        except Exception as e:
            print(f"Error leyendo {ruta}: {e}")
            return None

    def _encontrar_columna(self, df, posibles):
        for col in df.columns:
            for p in posibles:
                if p in col.upper():
                    return col
        return None

    # -------------------------------------------------------------------
    # Carga de datos de fútbol (E0.csv)
    # -------------------------------------------------------------------
    def _cargar_soccer_stats(self) -> pd.DataFrame:
        archivo = os.path.join(self.carpeta, "E0.csv")
        if not os.path.exists(archivo):
            print("⚠️ No se encontró el archivo E0.csv (fútbol)")
            return pd.DataFrame()
        try:
            df = pd.read_csv(archivo)
            df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
            df.rename(columns={
                'Date': 'fecha',
                'HomeTeam': 'equipo_local',
                'AwayTeam': 'equipo_visitante',
                'FTHG': 'goles_local',
                'FTAG': 'goles_visitante',
                'HS': 'tiros_local',
                'AS': 'tiros_visitante',
                'HST': 'tiros_puerta_local',
                'AST': 'tiros_puerta_visitante',
                'HF': 'faltas_local',
                'AF': 'faltas_visitante',
                'HC': 'corners_local',
                'AC': 'corners_visitante',
                'HY': 'amarillas_local',
                'AY': 'amarillas_visitante',
                'HR': 'rojas_local',
                'AR': 'rojas_visitante'
            }, inplace=True)
            print(f"✓ Cargados {len(df)} partidos de fútbol desde {archivo}")
            return df
        except Exception as e:
            print(f"Error cargando E0.csv: {e}")
            return pd.DataFrame()

    # -------------------------------------------------------------------
    # Carga del calendario (schedule.csv o .xlsx)
    # -------------------------------------------------------------------
    def _cargar_schedule(self) -> pd.DataFrame:
        posibles = ["schedule.xlsx", "schedule.csv"]
        archivo = None
        for p in posibles:
            ruta = os.path.join(self.carpeta, p)
            if os.path.exists(ruta):
                archivo = ruta
                break
        if archivo is None:
            print("⚠️ No se encontró schedule.xlsx ni schedule.csv")
            return pd.DataFrame()
        try:
            if archivo.endswith('.csv'):
                df = pd.read_csv(archivo)
            else:
                df = pd.read_excel(archivo)
            df['fecha'] = pd.to_datetime(df['fecha'])
            print(f"✓ Calendario cargado: {len(df)} partidos programados.")
            return df
        except Exception as e:
            print(f"Error cargando schedule: {e}")
            return pd.DataFrame()

    # -------------------------------------------------------------------
    # Obtener métricas de un equipo de MLB (con mapeo inglés->español)
    # -------------------------------------------------------------------
    def _obtener_metricas_mlb(self, nombre_equipo: str) -> Dict[str, float]:
        # Convertir nombre inglés a español según mapeo
        nombre_es = NOMBRES_INGLES_A_ESPANOL.get(nombre_equipo, nombre_equipo)
        # Normalizar para búsqueda flexible
        norm_busqueda = normalizar_nombre(nombre_es)

        # 1. Búsqueda exacta
        if nombre_es in self.mlb_stats:
            return self.mlb_stats[nombre_es]

        # 2. Búsqueda por nombre normalizado
        for k in self.mlb_stats:
            if normalizar_nombre(k) == norm_busqueda:
                return self.mlb_stats[k]

        # 3. Coincidencia parcial (para nombres como "Diamondbacks de Arizona" vs "Arizona Diamondbacks")
        for k in self.mlb_stats:
            norm_k = normalizar_nombre(k)
            if norm_busqueda in norm_k or norm_k in norm_busqueda:
                return self.mlb_stats[k]

        print(f"  ⚠️ Equipo '{nombre_equipo}' no encontrado en estadísticas.")
        return {}

    # -------------------------------------------------------------------
    # Modelo de probabilidad MLB usando AVG y TRAPO
    # -------------------------------------------------------------------
    def _calcular_probabilidad_mlb(self, local: Dict, visitante: Dict) -> float:
        def norm(value, is_lower_better=False, max_val=5.0):
            if value is None:
                return 0.5
            if is_lower_better:
                if value <= 0:
                    return 1.0
                if value > 10:
                    return 0.0
                return max(0, min(1, (max_val - value) / max_val))
            else:
                if value <= 0:
                    return 0.0
                if value > 0.4:
                    return 1.0
                return max(0, min(1, value / max_val))

        trapo_local = norm(local.get('TRAPO'), True)
        trapo_visit = norm(visitante.get('TRAPO'), True)
        avg_local = norm(local.get('AVG'), max_val=0.35)
        avg_visit = norm(visitante.get('AVG'), max_val=0.35)

        score_local = (trapo_local - trapo_visit) + (avg_local - avg_visit)
        prob_local = 0.5 + score_local * 0.2
        return max(0.05, min(0.95, prob_local))

    # -------------------------------------------------------------------
    # Fútbol
    # -------------------------------------------------------------------
    def _obtener_metricas_soccer(self, equipo: str, fecha: date) -> Dict[str, float]:
        df = self.soccer_stats
        if df.empty:
            return {}
        mask_local = (df['equipo_local'] == equipo) & (df['fecha'] <= pd.to_datetime(fecha))
        mask_visit = (df['equipo_visitante'] == equipo) & (df['fecha'] <= pd.to_datetime(fecha))
        partidos = []
        for _, row in df[mask_local].iterrows():
            partidos.append({
                'goles_favor': row['goles_local'],
                'goles_contra': row['goles_visitante'],
                'tiros': row.get('tiros_local'),
                'tiros_puerta': row.get('tiros_puerta_local'),
            })
        for _, row in df[mask_visit].iterrows():
            partidos.append({
                'goles_favor': row['goles_visitante'],
                'goles_contra': row['goles_local'],
                'tiros': row.get('tiros_visitante'),
                'tiros_puerta': row.get('tiros_puerta_visitante'),
            })
        if not partidos:
            return {}
        n = len(partidos)
        return {
            'avg_goals_for': sum(p['goles_favor'] for p in partidos) / n,
            'avg_goals_against': sum(p['goles_contra'] for p in partidos) / n,
            'avg_shots': sum(p.get('tiros', 0) for p in partidos) / n if partidos[0].get('tiros') is not None else None,
            'avg_shots_on_target': sum(p.get('tiros_puerta', 0) for p in partidos) / n if partidos[0].get('tiros_puerta') is not None else None,
        }

    def _calcular_probabilidad_soccer(self, local: Dict, visitante: Dict) -> float:
        gf_local = local.get('avg_goals_for', 1.2)
        gf_visit = visitante.get('avg_goals_for', 1.2)
        gc_local = local.get('avg_goals_against', 1.2)
        gc_visit = visitante.get('avg_goals_against', 1.2)
        diff_gf = gf_local - gf_visit
        diff_gc = gc_visit - gc_local
        score_local = diff_gf + diff_gc
        prob_local = 0.5 + score_local * 0.15
        return max(0.05, min(0.95, prob_local))

    # -------------------------------------------------------------------
    # Método principal
    # -------------------------------------------------------------------
    def analizar_juegos_dia(self, fecha: date) -> List[Prediccion]:
        if self.schedule.empty:
            print("No hay calendario cargado.")
            return []

        fecha_dt = pd.to_datetime(fecha)
        df_hoy = self.schedule[self.schedule['fecha'].dt.date == fecha_dt.date()]
        if df_hoy.empty:
            print(f"No hay partidos programados para {fecha}.")
            return []

        # Contar partidos por deporte para advertencia
        deportes = df_hoy['deporte'].value_counts()
        if 'soccer' not in deportes:
            print("⚠️ No hay partidos de fútbol en el calendario. Para analizar fútbol, agrega partidos con deporte 'soccer' en schedule.csv/.xlsx.")
        if 'mlb' not in deportes:
            print("⚠️ No hay partidos de béisbol en el calendario.")

        predicciones = []
        debug_mostrados = 0
        for _, row in df_hoy.iterrows():
            deporte = row.get('deporte', 'mlb').lower()
            local = row['equipo_local']
            visitante = row['equipo_visitante']

            if deporte == 'mlb':
                stats_local = self._obtener_metricas_mlb(local)
                stats_visit = self._obtener_metricas_mlb(visitante)
                if not stats_local or not stats_visit:
                    continue
                prob_local = self._calcular_probabilidad_mlb(stats_local, stats_visit)
                ganador = local if prob_local > 0.5 else visitante
                prob = max(prob_local, 1 - prob_local)
                comentario = (f"Basado en AVG ({stats_local.get('AVG','N/A')} vs {stats_visit.get('AVG','N/A')}) "
                              f"y carreras permitidas/juego ({stats_local.get('TRAPO','N/A')} vs {stats_visit.get('TRAPO','N/A')}).")
                # DEBUG: Mostrar los primeros 5 partidos con su equipo favorito y probabilidad
                if debug_mostrados < 5:
                    print(f"  DEBUG: {local} vs {visitante}")
                    print(f"         → Favorito: {ganador} con {prob:.2%} de probabilidad")
                    debug_mostrados += 1
            elif deporte == 'soccer':
                stats_local = self._obtener_metricas_soccer(local, fecha)
                stats_visit = self._obtener_metricas_soccer(visitante, fecha)
                prob_local = self._calcular_probabilidad_soccer(stats_local, stats_visit)
                ganador = local if prob_local > 0.5 else visitante
                prob = max(prob_local, 1 - prob_local)
                comentario = (f"Promedio goles últimos 5: {local} {stats_local.get('avg_goals_for',0):.2f} a favor, "
                              f"{stats_local.get('avg_goals_against',0):.2f} en contra; "
                              f"{visitante} {stats_visit.get('avg_goals_for',0):.2f} a favor, "
                              f"{stats_visit.get('avg_goals_against',0):.2f} en contra.")
                if debug_mostrados < 5:
                    print(f"  DEBUG: {local} vs {visitante}")
                    print(f"         → Favorito: {ganador} con {prob:.2%} de probabilidad")
                    debug_mostrados += 1
            else:
                continue

            if prob < UMBRAL_PROBABILIDAD:
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