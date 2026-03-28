# analista_futbol.py
"""
Analista especializado exclusivamente en fútbol (soccer).
Consulta directamente los proveedores de fútbol: TheSportsDB, OpenLigaDB, BBC.
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

from models import Prediccion
from config import UMBRAL_PROBABILIDAD, ENABLE_BBC_SPORT

# Importar proveedores de fútbol
from data_providers import TheSportsDBProvider, OpenLigaDBProvider
if ENABLE_BBC_SPORT:
    from data_providers import BBCSportProvider

# También necesitamos el DataProviderManager para obtener récord de equipos
from data_providers import DataProviderManager
data_manager = DataProviderManager()


class AnalistaFutbol:
    """
    Analista que solo analiza partidos de fútbol, consultando directamente
    a los proveedores especializados.
    """

    def __init__(self):
        self.nombre = "Analista Fútbol"
        # Instanciar proveedores de fútbol
        self.providers = [TheSportsDBProvider(), OpenLigaDBProvider()]
        if ENABLE_BBC_SPORT:
            self.providers.append(BBCSportProvider())

    def _obtener_juegos_futbol(self, fecha: date) -> List[Dict[str, Any]]:
        """
        Consulta secuencialmente los proveedores de fútbol y combina los juegos.
        Retorna una lista de juegos (dict) con los campos estandarizados.
        """
        juegos = []
        for provider in self.providers:
            print(f"  Intentando obtener datos de fútbol desde {provider.name}...")
            try:
                datos = provider.get_games_by_date(fecha)
                if datos:
                    # Filtrar solo los que son de fútbol (por si acaso)
                    juegos_futbol = [j for j in datos if j.get("sport") == "soccer"]
                    if juegos_futbol:
                        print(f"  ✓ {provider.name} devolvió {len(juegos_futbol)} partidos de fútbol.")
                        # Mostrar ejemplo del primer partido para depuración
                        ejemplo = juegos_futbol[0]
                        print(f"     Ejemplo: {ejemplo.get('home_team')} vs {ejemplo.get('away_team')} - Estado: {ejemplo.get('status')}")
                        juegos.extend(juegos_futbol)
                    else:
                        print(f"  ✗ {provider.name} no devolvió partidos de fútbol.")
                else:
                    print(f"  ✗ {provider.name} no devolvió datos.")
            except Exception as e:
                print(f"  ✗ Error en {provider.name}: {e}")
        return juegos

    def _obtener_datos_rendimiento(self, team_name: str, fecha: date) -> Dict[str, Any]:
        """
        Obtiene datos de rendimiento del equipo (últimos 5 y 14 días) usando el manager general.
        """
        record_14 = data_manager.get_team_recent_record(team_name, fecha, "soccer")
        # Calcular últimos 5 días manualmente
        start_5 = fecha - timedelta(days=5)
        wins_5 = 0
        losses_5 = 0
        total_goals_for = 0
        total_goals_against = 0
        games_5 = 0

        current_date = start_5
        while current_date <= fecha:
            # Obtener todos los juegos del día (del manager general, no solo fútbol)
            juegos = data_manager.get_games_by_date(current_date)
            for juego in juegos:
                if juego.get("sport") != "soccer":
                    continue
                if juego.get("home_team") == team_name or juego.get("away_team") == team_name:
                    if juego.get("status") not in ["finished", "post", "final"]:
                        continue
                    home_score = juego.get("home_score")
                    away_score = juego.get("away_score")
                    if home_score is None or away_score is None:
                        continue
                    is_home = (juego.get("home_team") == team_name)
                    team_score = home_score if is_home else away_score
                    opp_score = away_score if is_home else home_score
                    if team_score > opp_score:
                        wins_5 += 1
                    else:
                        losses_5 += 1
                    total_goals_for += team_score
                    total_goals_against += opp_score
                    games_5 += 1
            current_date += timedelta(days=1)

        avg_for = total_goals_for / games_5 if games_5 > 0 else None
        avg_against = total_goals_against / games_5 if games_5 > 0 else None

        return {
            'wins_14': record_14['wins'],
            'losses_14': record_14['losses'],
            'wins_5': wins_5,
            'losses_5': losses_5,
            'avg_goals_for': avg_for,
            'avg_goals_against': avg_against,
            'games_5': games_5
        }

    def _calcular_probabilidad(self, local_data: Dict, visitante_data: Dict) -> float:
        """
        Modelo específico para fútbol.
        """
        def win_pct(w, l):
            total = w + l
            return w / total if total > 0 else 0.5

        pct14_local = win_pct(local_data['wins_14'], local_data['losses_14'])
        pct14_visit = win_pct(visitante_data['wins_14'], visitante_data['losses_14'])
        pct5_local = win_pct(local_data['wins_5'], local_data['losses_5'])
        pct5_visit = win_pct(visitante_data['wins_5'], visitante_data['losses_5'])

        diff14 = pct14_local - pct14_visit
        diff5 = pct5_local - pct5_visit

        # Diferencia de goles
        goals_factor = 0
        if local_data['avg_goals_for'] is not None and visitante_data['avg_goals_for'] is not None:
            diff_goals = (local_data['avg_goals_for'] - local_data['avg_goals_against']) - \
                         (visitante_data['avg_goals_for'] - visitante_data['avg_goals_against'])
            max_diff = 2.0
            goals_factor = diff_goals / max_diff
            goals_factor = max(-0.2, min(0.2, goals_factor))

        prob_local = 0.5
        prob_local += diff14 * 0.20
        prob_local += diff5 * 0.35
        prob_local += goals_factor * 0.25
        prob_local += 0.05  # localía

        return max(0.05, min(0.95, prob_local))

    def _generar_comentario(self, local_data: Dict, visitante_data: Dict,
                            home_name: str, away_name: str, prob_local: float) -> str:
        def pct(w, l):
            total = w + l
            return w / total if total > 0 else 0.5

        pct14_local = pct(local_data['wins_14'], local_data['losses_14'])
        pct14_visit = pct(visitante_data['wins_14'], visitante_data['losses_14'])
        pct5_local = pct(local_data['wins_5'], local_data['losses_5'])
        pct5_visit = pct(visitante_data['wins_5'], visitante_data['losses_5'])

        comentario = f"🏆 PREDICCIÓN FÚTBOL: {'LOCAL' if prob_local > 0.5 else 'VISITANTE'} gana con {max(prob_local, 1-prob_local)*100:.1f}% de probabilidad.\n\n"
        comentario += "🔍 Factores:\n"
        comentario += f"• Récord últimos 14 días: {home_name} {pct14_local:.1%} vs {away_name} {pct14_visit:.1%}\n"
        comentario += f"• Récord últimos 5 días: {home_name} {pct5_local:.1%} vs {away_name} {pct5_visit:.1%} (mayor peso)\n"
        if local_data['avg_goals_for'] is not None:
            comentario += f"• Goles promedio últimos 5 partidos: {home_name} {local_data['avg_goals_for']:.2f} a favor / {local_data['avg_goals_against']:.2f} en contra | "
            comentario += f"{away_name} {visitante_data['avg_goals_for']:.2f} a favor / {visitante_data['avg_goals_against']:.2f} en contra\n"
        comentario += "• Ventaja de localía: +5% en la probabilidad"
        return comentario

    def analizar_juegos_dia(self, fecha: date) -> List[Prediccion]:
        """
        Analiza solo los partidos de fútbol del día.
        """
        print(f"\n--- {self.nombre} analizando juegos de fútbol para {fecha} ---")

        # Obtener juegos de fútbol directamente de los proveedores especializados
        juegos = self._obtener_juegos_futbol(fecha)

        if not juegos:
            print("No se encontraron partidos de fútbol para hoy en ninguna fuente.")
            return []

        # Filtrar solo los que no han finalizado
        juegos_programados = []
        for j in juegos:
            status = j.get("status", "").lower()
            # Considerar programados aquellos cuyo estado NO sea "finished", "post", "final"
            if status in ["finished", "post", "final"]:
                continue
            juegos_programados.append(j)

        if not juegos_programados:
            print(f"Se encontraron {len(juegos)} partidos, pero todos ya han finalizado.")
            # Opcional: mostrar algunos ejemplos
            for j in juegos[:3]:
                print(f"  {j.get('home_team')} vs {j.get('away_team')} - Estado: {j.get('status')}")
            return []

        print(f"  Se encontraron {len(juegos_programados)} partidos programados para hoy.")

        predicciones = []
        for juego in juegos_programados:
            home_name = juego.get("home_team", "")
            away_name = juego.get("away_team", "")
            if not home_name or not away_name:
                continue

            print(f"  Analizando {home_name} vs {away_name}...")

            # Obtener datos de rendimiento
            local_data = self._obtener_datos_rendimiento(home_name, fecha)
            visitante_data = self._obtener_datos_rendimiento(away_name, fecha)

            prob_local = self._calcular_probabilidad(local_data, visitante_data)
            prob = max(prob_local, 1 - prob_local)
            ganador = home_name if prob_local > 0.5 else away_name

            if prob < UMBRAL_PROBABILIDAD:
                continue

            comentario = self._generar_comentario(local_data, visitante_data,
                                                  home_name, away_name, prob_local)

            pred = Prediccion(
                fecha=fecha,
                equipo_local=home_name,
                equipo_visitante=away_name,
                ganador_predicho=ganador,
                probabilidad=prob,
                deporte="⚽ FÚTBOL",
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