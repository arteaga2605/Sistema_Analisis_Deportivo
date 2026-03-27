# analista_alternativo.py
"""
Segundo analista que utiliza un modelo de regresión basado en:
- Récord reciente (últimos 5 y 14 días)
- Diferencia de puntos/goles en partidos recientes
- Factor localía
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
import math

from models import Prediccion
from config import UMBRAL_PROBABILIDAD, USE_MULTI_PROVIDER

if USE_MULTI_PROVIDER:
    from data_providers import DataProviderManager
    data_manager = DataProviderManager()


class AnalistaAlternativo:
    def __init__(self):
        self.nombre = "Analista Avanzado"
        self.use_multi_provider = USE_MULTI_PROVIDER

    def _obtener_datos_rendimiento(self, team_name: str, fecha: date, sport: str) -> Dict[str, Any]:
        """
        Obtiene datos de rendimiento reales (récord y promedio de puntos/goles)
        usando el proveedor actual. Retorna un diccionario con:
        - wins_14: victorias últimos 14 días
        - losses_14: derrotas últimos 14 días
        - wins_5: victorias últimos 5 días (más reciente)
        - losses_5: derrotas últimos 5 días
        - avg_points_for: promedio de puntos/goles a favor últimos 5 partidos (si disponible)
        - avg_points_against: promedio de puntos/goles en contra últimos 5 partidos
        """
        record_14 = data_manager.get_team_recent_record(team_name, fecha, sport)
        # Para últimos 5 días, necesitamos consultar el récord con menos días
        start_5 = fecha - timedelta(days=5)
        wins_5 = 0
        losses_5 = 0
        total_points_for = 0
        total_points_against = 0
        games_5 = 0
        
        # Obtener juegos de los últimos 5 días desde el manager
        current_date = start_5
        while current_date <= fecha:
            juegos = data_manager.get_games_by_date(current_date)
            for juego in juegos:
                if juego.get("sport") != sport:
                    continue
                if juego.get("home_team") == team_name or juego.get("away_team") == team_name:
                    if juego.get("status") not in ["post", "finished"]:
                        continue
                    home_score = juego.get("home_score")
                    away_score = juego.get("away_score")
                    if home_score is None or away_score is None:
                        continue
                    # Convertir a entero si son strings
                    try:
                        home_score = int(home_score)
                        away_score = int(away_score)
                    except (ValueError, TypeError):
                        continue
                    is_home = (juego.get("home_team") == team_name)
                    team_score = home_score if is_home else away_score
                    opp_score = away_score if is_home else home_score
                    if team_score > opp_score:
                        wins_5 += 1
                    else:
                        losses_5 += 1
                    total_points_for += team_score
                    total_points_against += opp_score
                    games_5 += 1
            current_date += timedelta(days=1)
        
        avg_for = total_points_for / games_5 if games_5 > 0 else None
        avg_against = total_points_against / games_5 if games_5 > 0 else None
        
        return {
            'wins_14': record_14['wins'],
            'losses_14': record_14['losses'],
            'wins_5': wins_5,
            'losses_5': losses_5,
            'avg_points_for': avg_for,
            'avg_points_against': avg_against,
            'games_5': games_5
        }

    def _calcular_probabilidad_avanzada(self, local_data: Dict, visitante_data: Dict, sport: str) -> float:
        """
        Modelo de regresión logística simplificado:
        - factor_win_pct_14: diferencia de porcentaje de victorias en 14 días
        - factor_win_pct_5: diferencia de porcentaje en 5 días (más peso)
        - factor_points_diff: diferencia de promedio de puntos (si hay datos)
        - home_advantage: +0.05 (5% adicional por localía)
        """
        # Calcular porcentajes de victoria
        def win_pct(w, l):
            total = w + l
            return w / total if total > 0 else 0.5
        
        pct14_local = win_pct(local_data['wins_14'], local_data['losses_14'])
        pct14_visit = win_pct(visitante_data['wins_14'], visitante_data['losses_14'])
        
        pct5_local = win_pct(local_data['wins_5'], local_data['losses_5'])
        pct5_visit = win_pct(visitante_data['wins_5'], visitante_data['losses_5'])
        
        # Diferencia de porcentajes (positivo = local mejor)
        diff14 = pct14_local - pct14_visit
        diff5 = pct5_local - pct5_visit
        
        # Factor puntos (si hay datos)
        points_factor = 0
        if local_data['avg_points_for'] is not None and visitante_data['avg_points_for'] is not None:
            if sport in ['basketball', 'nba', 'nhl', 'soccer']:
                diff_points = (local_data['avg_points_for'] - local_data['avg_points_against']) - \
                              (visitante_data['avg_points_for'] - visitante_data['avg_points_against'])
                max_diff = 20 if sport in ['basketball', 'nba'] else 5 if sport == 'nhl' else 2
                points_factor = diff_points / max_diff
                points_factor = max(-0.2, min(0.2, points_factor))
        
        # Combinar factores (pesos)
        prob_local = 0.5
        prob_local += diff14 * 0.2          # récord 14 días: 20% de peso
        prob_local += diff5 * 0.35          # récord 5 días: 35% de peso (más reciente)
        prob_local += points_factor * 0.25   # diferencia de puntos: 25%
        prob_local += 0.05                  # ventaja localía base: 5%
        
        # Limitar a rango [0.05, 0.95]
        prob_local = max(0.05, min(0.95, prob_local))
        return prob_local

    def _generar_comentario_avanzado(self, local_data: Dict, visitante_data: Dict,
                                      home_name: str, away_name: str,
                                      prob_local: float, sport: str) -> str:
        """
        Comentario explicando los factores que determinaron la predicción.
        """
        pct14_local = local_data['wins_14'] / (local_data['wins_14'] + local_data['losses_14']) if (local_data['wins_14'] + local_data['losses_14']) > 0 else 0.5
        pct14_visit = visitante_data['wins_14'] / (visitante_data['wins_14'] + visitante_data['losses_14']) if (visitante_data['wins_14'] + visitante_data['losses_14']) > 0 else 0.5
        
        pct5_local = local_data['wins_5'] / (local_data['wins_5'] + local_data['losses_5']) if (local_data['wins_5'] + local_data['losses_5']) > 0 else 0.5
        pct5_visit = visitante_data['wins_5'] / (visitante_data['wins_5'] + visitante_data['losses_5']) if (visitante_data['wins_5'] + visitante_data['losses_5']) > 0 else 0.5
        
        comentario = f"🏆 PREDICCIÓN (Modelo avanzado): {'LOCAL' if prob_local > 0.5 else 'VISITANTE'} gana con {max(prob_local, 1-prob_local)*100:.1f}% de probabilidad.\n\n"
        comentario += "🔍 Factores considerados:\n"
        comentario += f"• Récord últimos 14 días: {home_name} {pct14_local:.1%} vs {away_name} {pct14_visit:.1%}\n"
        comentario += f"• Récord últimos 5 días: {home_name} {pct5_local:.1%} vs {away_name} {pct5_visit:.1%} (mayor peso)\n"
        
        if local_data['avg_points_for'] is not None:
            comentario += f"• Promedio puntos/goles últimos 5 partidos: {home_name} {local_data['avg_points_for']:.1f} a favor / {local_data['avg_points_against']:.1f} en contra | "
            comentario += f"{away_name} {visitante_data['avg_points_for']:.1f} a favor / {visitante_data['avg_points_against']:.1f} en contra\n"
        
        comentario += "• Ventaja de localía: +5% en la probabilidad\n"
        
        if prob_local > 0.65:
            comentario += "\n✅ Factor decisivo: Mejor forma reciente y rendimiento ofensivo."
        else:
            comentario += "\n⚠️ Partido muy equilibrado, pequeña ventaja por localía y últimos resultados."
        
        return comentario

    def analizar_juegos_dia(self, fecha: date) -> List[Prediccion]:
        """
        Analiza los juegos del día usando el modelo avanzado.
        """
        print(f"\n--- {self.nombre} analizando juegos para {fecha} ---")
        
        if not self.use_multi_provider:
            print("Multi-proveedor desactivado. No se pueden obtener datos.")
            return []
        
        juegos_raw = data_manager.get_games_by_date(fecha)
        juegos = [j for j in juegos_raw if j.get("status") not in ["post", "finished", "final"]]
        
        if not juegos:
            print("No se encontraron juegos programados.")
            return []
        
        predicciones = []
        for juego in juegos:
            home_name = juego.get("home_team", "")
            away_name = juego.get("away_team", "")
            sport = juego.get("sport", "mlb")
            if not home_name or not away_name:
                continue
            
            print(f"  Analizando {home_name} vs {away_name} ({sport})...")
            
            # Obtener datos de rendimiento reales
            local_data = self._obtener_datos_rendimiento(home_name, fecha, sport)
            visitante_data = self._obtener_datos_rendimiento(away_name, fecha, sport)
            
            # Calcular probabilidad con modelo avanzado
            prob_local = self._calcular_probabilidad_avanzada(local_data, visitante_data, sport)
            prob = max(prob_local, 1 - prob_local)
            ganador = home_name if prob_local > 0.5 else away_name
            
            if prob < UMBRAL_PROBABILIDAD:
                continue
            
            comentario = self._generar_comentario_avanzado(local_data, visitante_data,
                                                           home_name, away_name,
                                                           prob_local, sport)
            
            sport_display = {
                "mlb": "⚾ MLB",
                "nfl": "🏈 NFL",
                "nba": "🏀 NBA",
                "basketball": "🏀 NBA",
                "nhl": "🏒 NHL",
                "soccer": "⚽ FÚTBOL"
            }.get(sport, sport.upper())
            
            pred = Prediccion(
                fecha=fecha,
                equipo_local=home_name,
                equipo_visitante=away_name,
                ganador_predicho=ganador,
                probabilidad=prob,
                deporte=sport_display,
                marcador_estimado=None,
                comentario=comentario,
                analista=self.nombre
            )
            predicciones.append(pred)
        
        predicciones.sort(key=lambda p: p.probabilidad, reverse=True)
        if len(predicciones) < 8:
            print(f"{self.nombre}: Solo {len(predicciones)} partidos con prob ≥ {UMBRAL_PROBABILIDAD*100:.0f}%.")
        else:
            print(f"{self.nombre}: {len(predicciones)} partidos con alta probabilidad.")
        return predicciones