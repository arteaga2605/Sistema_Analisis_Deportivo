# analista_excel.py
"""
Analista offline que obtiene datos históricos desde un archivo Excel.
No requiere conexión a internet.
"""

import pandas as pd
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
import os

from models import Prediccion
from config import UMBRAL_PROBABILIDAD

class AnalistaExcel:
    """
    Analista que lee estadísticas desde un archivo Excel local.
    """

    def __init__(self):
        self.nombre = "Analista Excel"
        self.excel_path = "datos_historicos.xlsx"
        self.df = None
        self._cargar_datos()

    def _cargar_datos(self):
        """Carga el archivo Excel en un DataFrame."""
        if not os.path.exists(self.excel_path):
            print(f"⚠️ Archivo {self.excel_path} no encontrado. Se creará uno de ejemplo.")
            self._crear_archivo_ejemplo()
            self.df = pd.read_excel(self.excel_path, sheet_name="partidos")
        else:
            try:
                self.df = pd.read_excel(self.excel_path, sheet_name="partidos")
                print(f"✅ Datos cargados desde {self.excel_path} ({len(self.df)} registros)")
            except Exception as e:
                print(f"❌ Error al cargar {self.excel_path}: {e}")
                self.df = pd.DataFrame()

    def _crear_archivo_ejemplo(self):
        """Crea un archivo Excel de ejemplo con datos simulados."""
        from datetime import datetime

        # Datos de ejemplo para demostración
        datos = {
            "fecha": [datetime(2025, 10, 1), datetime(2025, 10, 1), datetime(2025, 10, 2)],
            "equipo_local": ["Los Angeles Dodgers", "Real Madrid", "Boston Celtics"],
            "equipo_visitante": ["New York Yankees", "Barcelona", "Los Angeles Lakers"],
            "goles_local": [5, 2, 110],
            "goles_visitante": [3, 1, 105],
            "posesion_local": [55, 58, 52],
            "posesion_visitante": [45, 42, 48],
            "tiros_local": [12, 15, 95],
            "tiros_visitante": [8, 7, 92],
            "deporte": ["mlb", "soccer", "nba"],
            "resultado": ["local", "local", "local"]
        }
        df = pd.DataFrame(datos)
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(self.excel_path) if os.path.dirname(self.excel_path) else '.', exist_ok=True)
        with pd.ExcelWriter(self.excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name="partidos", index=False)
        print(f"📄 Archivo ejemplo creado: {self.excel_path}")

    def _obtener_rendimiento_equipo(self, equipo: str, fecha: date, deporte: str) -> Dict[str, float]:
        """
        Calcula rendimiento histórico del equipo basado en partidos anteriores en el Excel.
        Retorna: porcentaje de victorias, promedio de goles/puntos a favor y en contra.
        """
        if self.df is None or self.df.empty:
            return {'win_pct': 0.5, 'avg_for': 0, 'avg_against': 0, 'num_partidos': 0}

        # Filtrar partidos donde el equipo es local o visitante, con fecha anterior a la dada
        df_filtrado = self.df[
            ((self.df['equipo_local'] == equipo) | (self.df['equipo_visitante'] == equipo)) &
            (pd.to_datetime(self.df['fecha']).dt.date < fecha) &
            (self.df['deporte'] == deporte)
        ]

        if df_filtrado.empty:
            return {'win_pct': 0.5, 'avg_for': 0, 'avg_against': 0, 'num_partidos': 0}

        wins = 0
        total_for = 0
        total_against = 0
        for _, row in df_filtrado.iterrows():
            is_local = (row['equipo_local'] == equipo)
            goles_local = row['goles_local']
            goles_visitante = row['goles_visitante']
            goles_equipo = goles_local if is_local else goles_visitante
            goles_rival = goles_visitante if is_local else goles_local
            total_for += goles_equipo
            total_against += goles_rival
            if goles_equipo > goles_rival:
                wins += 1

        num = len(df_filtrado)
        return {
            'win_pct': wins / num,
            'avg_for': total_for / num,
            'avg_against': total_against / num,
            'num_partidos': num
        }

    def _calcular_probabilidad(self, local_data: Dict, visitante_data: Dict) -> float:
        """
        Calcula probabilidad de victoria local basado en rendimiento histórico.
        """
        # Diferencia de porcentajes de victoria
        pct_local = local_data['win_pct']
        pct_visitante = visitante_data['win_pct']
        diff_pct = pct_local - pct_visitante

        # Diferencia de promedio de goles/puntos (normalizada)
        diff_avg = (local_data['avg_for'] - local_data['avg_against']) - (visitante_data['avg_for'] - visitante_data['avg_against'])
        max_diff = 10  # valor máximo esperado de diferencia (ajustable)
        diff_avg_norm = max(-0.2, min(0.2, diff_avg / max_diff))

        # Combinar factores (pesos)
        prob_local = 0.5
        prob_local += diff_pct * 0.3      # 30% peso al porcentaje de victorias
        prob_local += diff_avg_norm * 0.25 # 25% peso a la diferencia de goles
        prob_local += 0.05                 # 5% ventaja localía base

        # Limitar
        prob_local = max(0.05, min(0.95, prob_local))
        return prob_local

    def _generar_comentario(self, local_data: Dict, visitante_data: Dict,
                            home_name: str, away_name: str, prob_local: float) -> str:
        """Genera comentario basado en datos históricos."""
        pct_local = local_data['win_pct'] * 100
        pct_visit = visitante_data['win_pct'] * 100
        comentario = f"🏆 PREDICCIÓN (OFFLINE): {'LOCAL' if prob_local > 0.5 else 'VISITANTE'} gana con {max(prob_local, 1-prob_local)*100:.1f}% de probabilidad.\n\n"
        comentario += "📊 Datos históricos (archivo Excel):\n"
        comentario += f"• {home_name}: {local_data['num_partidos']} partidos, {pct_local:.1f}% victorias, promedio {local_data['avg_for']:.1f} a favor / {local_data['avg_against']:.1f} en contra\n"
        comentario += f"• {away_name}: {visitante_data['num_partidos']} partidos, {pct_visit:.1f}% victorias, promedio {visitante_data['avg_for']:.1f} a favor / {visitante_data['avg_against']:.1f} en contra\n"
        comentario += "• Ventaja de localía: +5% en la probabilidad"
        return comentario

    def analizar_juegos_dia(self, fecha: date) -> List[Prediccion]:
        """
        Analiza los partidos del día utilizando el archivo Excel.
        Necesita que en el Excel existan registros para la fecha actual.
        """
        print(f"\n--- {self.nombre} analizando juegos para {fecha} ---")

        if self.df is None or self.df.empty:
            print("⚠️ No hay datos en el archivo Excel.")
            return []

        # Filtrar partidos que coincidan con la fecha actual
        df_hoy = self.df[pd.to_datetime(self.df['fecha']).dt.date == fecha]
        if df_hoy.empty:
            print(f"No se encontraron partidos para la fecha {fecha} en el Excel.")
            return []

        predicciones = []
        for _, row in df_hoy.iterrows():
            home_name = row['equipo_local']
            away_name = row['equipo_visitante']
            deporte = row['deporte']

            # Obtener rendimiento histórico
            local_data = self._obtener_rendimiento_equipo(home_name, fecha, deporte)
            visitante_data = self._obtener_rendimiento_equipo(away_name, fecha, deporte)

            # Calcular probabilidad
            prob_local = self._calcular_probabilidad(local_data, visitante_data)
            prob = max(prob_local, 1 - prob_local)
            ganador = home_name if prob_local > 0.5 else away_name

            if prob < UMBRAL_PROBABILIDAD:
                continue

            comentario = self._generar_comentario(local_data, visitante_data,
                                                  home_name, away_name, prob_local)

            # Nombre del deporte para mostrar
            sport_display = {
                "mlb": "⚾ MLB",
                "nfl": "🏈 NFL",
                "nba": "🏀 NBA",
                "nhl": "🏒 NHL",
                "soccer": "⚽ FÚTBOL"
            }.get(deporte, deporte.upper())

            pred = Prediccion(
                fecha=fecha,
                equipo_local=home_name,
                equipo_visitante=away_name,
                ganador_predicho=ganador,
                probabilidad=prob,
                deporte=sport_display,
                comentario=comentario,
                analista=self.nombre
            )
            predicciones.append(pred)

        predicciones.sort(key=lambda p: p.probabilidad, reverse=True)
        print(f"{self.nombre}: {len(predicciones)} partidos con probabilidad >= {UMBRAL_PROBABILIDAD*100:.0f}%.")
        return predicciones