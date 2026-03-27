# social_sentiment.py
"""
Módulo para análisis de sentimiento en redes sociales.
Por ahora simula datos basados en estadísticas del equipo.
En el futuro se puede conectar a APIs reales.
"""

from typing import Dict, Any, Optional
import random


class SocialSentimentAnalyzer:
    """
    Analiza el sentimiento público hacia un equipo.
    """

    def __init__(self):
        pass

    def get_team_sentiment(self, team_name: str, sport: str, team_stats: Optional[Any] = None) -> float:
        """
        Retorna un valor entre -1 (muy negativo) y 1 (muy positivo).
        Simula basado en el récord o estadísticas.
        """
        if team_stats:
            # Si hay estadísticas, usar performance para calcular sentimiento
            if sport == 'mlb':
                # Usar AVG y ERA
                avg = team_stats.avg if team_stats.avg else 0.250
                era = team_stats.era if team_stats.era else 4.0
                sentiment = (avg - 0.250) * 5 + (4.0 - era) * 0.2
            elif sport == 'basketball':
                # Usar ofensiva y defensiva
                off = team_stats.off_rating if team_stats.off_rating else 105
                def_rating = team_stats.def_rating if team_stats.def_rating else 105
                sentiment = (off - 105) / 15 + (105 - def_rating) / 15
            elif sport == 'soccer':
                # Usar posesión y xG
                pos = team_stats.possession if team_stats.possession else 50
                xg = team_stats.xg_for if team_stats.xg_for else 1.2
                sentiment = (pos - 50) / 30 + (xg - 1.2) / 1.5
            elif sport == 'nhl':
                # Usar SV% y GAA
                sv = team_stats.sv_percent if team_stats.sv_percent else 0.910
                gaa = team_stats.gaa if team_stats.gaa else 2.8
                sentiment = (sv - 0.910) * 10 + (2.8 - gaa) * 0.5
            elif sport == 'nfl':
                # Usar QBR
                qbr = team_stats.qbr if team_stats.qbr else 50
                sentiment = (qbr - 50) / 30
            else:
                sentiment = 0
        else:
            # Sin estadísticas, usar aleatorio con sesgo neutro
            sentiment = random.uniform(-0.3, 0.3)

        # Limitar a [-1, 1]
        sentiment = max(-1.0, min(1.0, sentiment))
        return sentiment

    def get_match_sentiment(self, home_team: str, away_team: str, sport: str,
                            home_stats: Optional[Any] = None, away_stats: Optional[Any] = None) -> Dict[str, float]:
        """
        Retorna el sentimiento promedio y la confianza.
        """
        home_sent = self.get_team_sentiment(home_team, sport, home_stats)
        away_sent = self.get_team_sentiment(away_team, sport, away_stats)
        # El sentimiento del partido podría ser la diferencia o el promedio
        # Simplemente devolvemos ambos
        return {
            'home_sentiment': home_sent,
            'away_sentiment': away_sent,
            'public_favorite': home_team if home_sent > away_sent else away_team,
            'public_confidence': abs(home_sent - away_sent)  # diferencia como confianza
        }