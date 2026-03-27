# analista.py
from datetime import date, datetime
from typing import List

from apis import (
    get_schedule_by_date,
    get_team_recent_record,
    get_team_info,
    get_game_details
)
from models import Prediccion
from utils import calcular_probabilidad_ganador
from config import UMBRAL_PROBABILIDAD, DIAS_HISTORICO_RECIENTE, USE_MULTI_PROVIDER
from social_sentiment import SocialSentimentAnalyzer

if USE_MULTI_PROVIDER:
    from data_providers import DataProviderManager
    from statistics import TeamStats
    data_manager = DataProviderManager()

sentiment_analyzer = SocialSentimentAnalyzer()


class AnalistaDeportivo:
    """
    Analista principal que usa estadísticas básicas y récord reciente.
    """

    def __init__(self):
        self.nombre = "Analista Principal"
        self.use_multi_provider = USE_MULTI_PROVIDER

    def _generate_commentary(self, home_name: str, away_name: str, ganador: str, prob: float,
                             stats_home, stats_away, sport: str) -> str:
        """
        Genera un comentario personalizado basado en las estadísticas.
        """
        if stats_home and stats_away:
            # Comentario con estadísticas avanzadas
            if sport == 'mlb':
                if stats_home.era and stats_away.era:
                    return (f"El equipo {ganador} tiene ventaja en ERA ({stats_home.era if ganador == home_name else stats_away.era:.2f} vs "
                            f"{stats_away.era if ganador == home_name else stats_home.era:.2f}) y mejor ofensiva. Confianza alta.")
                else:
                    return f"Ventaja basada en diferencial de carreras y rendimiento reciente. Probabilidad {prob*100:.1f}%."
            elif sport == 'basketball':
                if stats_home.off_rating and stats_away.off_rating:
                    return (f"El equipo {ganador} tiene mejor rating ofensivo ({stats_home.off_rating if ganador == home_name else stats_away.off_rating:.1f} vs "
                            f"{stats_away.off_rating if ganador == home_name else stats_home.off_rating:.1f}) y defensa sólida.")
                else:
                    return f"Dominio en ofensiva y defensa según estadísticas recientes. Probabilidad {prob*100:.1f}%."
            elif sport == 'soccer':
                if stats_home.possession and stats_away.possession:
                    return (f"Mayor posesión ({stats_home.possession if ganador == home_name else stats_away.possession:.1f}%) y generación de xG favorable. "
                            f"Probabilidad {prob*100:.1f}%.")
                else:
                    return f"Control del partido y eficiencia ofensiva. Probabilidad {prob*100:.1f}%."
            elif sport == 'nhl':
                if stats_home.sv_percent and stats_away.sv_percent:
                    return (f"Mejor portero (SV% {stats_home.sv_percent if ganador == home_name else stats_away.sv_percent:.3f}) y control del juego. "
                            f"Probabilidad {prob*100:.1f}%.")
                else:
                    return f"Ventaja en juego de poder y defensa. Probabilidad {prob*100:.1f}%."
            else:
                return f"Análisis basado en estadísticas clave. Probabilidad {prob*100:.1f}%."
        else:
            # Comentario simple basado en récord
            return f"Basado en récord reciente de victorias/derrotas. Probabilidad {prob*100:.1f}%."

    def analizar_juegos_dia(self, fecha: date) -> List[Prediccion]:
        fecha_str = fecha.isoformat()
        print(f"Obteniendo juegos para {fecha_str}...")
        
        juegos = []
        
        if self.use_multi_provider:
            print("Usando sistema multi-proveedor con fallback automático...")
            juegos_raw = data_manager.get_games_by_date(fecha)
            # Filtrar solo juegos que aún no han comenzado
            for juego in juegos_raw:
                status = juego.get("status", "")
                if status in ["post", "finished", "final"]:
                    continue
                juegos.append(juego)
            if not juegos:
                print("No se encontraron juegos programados para hoy en el multi-proveedor. Intentando con MLB API...")
                juegos = get_schedule_by_date(fecha_str)
                juegos = [j for j in juegos if j.get('status', {}).get('codedGameState') in ('S', 'P', '?')]
        else:
            juegos = get_schedule_by_date(fecha_str)
            juegos = [j for j in juegos if j.get('status', {}).get('codedGameState') in ('S', 'P', '?')]
        
        if not juegos:
            print("No se encontraron juegos programados para esta fecha en ninguna fuente.")
            return []

        predicciones = []
        
        for juego in juegos:
            if self.use_multi_provider and isinstance(juego, dict):
                home_name = juego.get("home_team", "")
                away_name = juego.get("away_team", "")
                sport = juego.get("sport", "mlb")
                source = juego.get("source", "")
                
                if not home_name or not away_name:
                    continue
                
                # Intentar obtener estadísticas avanzadas
                stats_home = None
                stats_away = None
                if self.use_multi_provider:
                    stats_home = data_manager.get_team_stats(home_name, fecha, sport)
                    stats_away = data_manager.get_team_stats(away_name, fecha, sport)
                
                if stats_home and stats_away:
                    prob = stats_home.calculate_win_probability(stats_away)
                    ganador = home_name if prob > 0.5 else away_name
                    prob = max(prob, 1-prob)
                    # Estimar marcador
                    local_score, away_score = stats_home.estimate_score(stats_away)
                    marcador_estimado = f"{local_score}-{away_score}"
                else:
                    # Fallback: usar récord reciente
                    record_local = data_manager.get_team_recent_record(home_name, fecha, sport)
                    record_visitante = data_manager.get_team_recent_record(away_name, fecha, sport)
                    ganador_tipo, prob = calcular_probabilidad_ganador(record_local, record_visitante)
                    if ganador_tipo == "local":
                        ganador = home_name
                    else:
                        ganador = away_name
                    marcador_estimado = None
                    stats_home = None
                    stats_away = None
            else:
                # Formato MLB API original
                home_team = juego['teams']['home']['team']
                away_team = juego['teams']['away']['team']
                home_id = home_team['id']
                away_id = away_team['id']
                home_name = home_team['name']
                away_name = away_team['name']
                sport = "mlb"
                source = "MLB API"
                end_date = datetime.combine(fecha, datetime.min.time())
                record_local = get_team_recent_record(home_id, end_date)
                record_visitante = get_team_recent_record(away_id, end_date)
                ganador_tipo, prob = calcular_probabilidad_ganador(record_local, record_visitante)
                if ganador_tipo == "local":
                    ganador = home_name
                else:
                    ganador = away_name
                marcador_estimado = None
                stats_home = None
                stats_away = None
            
            if prob < UMBRAL_PROBABILIDAD:
                continue
            
            # Generar comentario personalizado
            comentario = self._generate_commentary(home_name, away_name, ganador, prob,
                                                   stats_home, stats_away, sport)
            
            # Determinar nombre del deporte para mostrar
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
                marcador_estimado=marcador_estimado,
                comentario=comentario,
                analista=self.nombre
            )
            predicciones.append(pred)
        
        predicciones.sort(key=lambda p: p.probabilidad, reverse=True)
        if len(predicciones) < 8:
            print(f"Advertencia: Solo se encontraron {len(predicciones)} partidos con probabilidad >= {UMBRAL_PROBABILIDAD*100:.0f}%.")
        else:
            print(f"Se encontraron {len(predicciones)} partidos con alta probabilidad. Mostrando los 8 primeros:")
            for i, p in enumerate(predicciones[:8], 1):
                print(f"{i}. {p.equipo_local} vs {p.equipo_visitante} -> Predicción: {p.ganador_predicho} (Probabilidad: {p.probabilidad*100:.1f}%)")
        
        return predicciones