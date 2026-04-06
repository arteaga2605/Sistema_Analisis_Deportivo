# analista_futbol.py
"""
Analista especializado exclusivamente en fútbol (soccer).
Consulta directamente los proveedores de fútbol: TheSportsDB, OpenLigaDB, API-Football, Football-Data.org.
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import requests
import random

from models import Prediccion
from config import UMBRAL_PROBABILIDAD, ENABLE_BBC_SPORT

# API Keys por defecto (pueden ser sobrescritas al instanciar)
DEFAULT_FOOTBALL_DATA_KEY = "16932c5260314df49e05d1ebf00948d9"
DEFAULT_API_FOOTBALL_KEY = "e729a8e693a40129047ce73db4944f2d"

# Intentar importar proveedores de fútbol
try:
    from data_providers import TheSportsDBProvider, OpenLigaDBProvider
    if ENABLE_BBC_SPORT:
        from data_providers import BBCSportProvider
    PROVIDERS_AVAILABLE = True
except ImportError:
    PROVIDERS_AVAILABLE = False
    print("⚠️ Proveedores de data_providers no disponibles. Usando APIs directas.")

# También necesitamos el DataProviderManager para obtener récord de equipos
try:
    from data_providers import DataProviderManager
    data_manager = DataProviderManager()
except ImportError:
    data_manager = None
    print("⚠️ DataProviderManager no disponible.")


class APIFootballProvider:
    """
    Proveedor usando API-Football (api-football.com).
    API Key: e729a8e693a40129047ce73db4944f2d
    """
    
    def __init__(self, api_key: str = None):
        self.name = "API-Football"
        self.base_url = "https://v3.football.api-sports.io"
        self.api_key = api_key or DEFAULT_API_FOOTBALL_KEY
        self.enabled = bool(self.api_key)
        self._team_stats_cache = {}
        
    def get_games_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        
        try:
            headers = {
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": "v3.football.api-sports.io"
            }
            
            # IDs de ligas principales
            league_ids = [
                39,   # Premier League
                140,  # La Liga
                135,  # Serie A
                78,   # Bundesliga
                61,   # Ligue 1
                2,    # Champions League
                3,    # Europa League
                94,   # Liga MX
                71,   # Brasileirão
                128,  # Liga Argentina
                262,  # Liga Portugal
                88,   # Eredivisie
                253,  # MLS
                98,   # J1 League
                292,  # K League
            ]
            
            date_str = target_date.strftime("%Y-%m-%d")
            all_fixtures = []
            
            for league_id in league_ids:
                try:
                    url = f"{self.base_url}/fixtures"
                    params = {
                        "date": date_str,
                        "league": league_id,
                        "season": target_date.year if target_date.month >= 7 else target_date.year - 1
                    }
                    
                    response = requests.get(url, headers=headers, params=params, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        fixtures = data.get("response", [])
                        
                        for fixture in fixtures:
                            fixture_data = fixture.get("fixture", {})
                            teams = fixture.get("teams", {})
                            goals = fixture.get("goals", {})
                            
                            status_short = fixture_data.get("status", {}).get("short", "")
                            
                            game = {
                                "id": fixture_data.get("id"),
                                "home_team": teams.get("home", {}).get("name"),
                                "away_team": teams.get("away", {}).get("name"),
                                "status": self._map_status(status_short),
                                "sport": "soccer",
                                "source": self.name,
                                "league": fixture.get("league", {}).get("name"),
                                "home_score": goals.get("home"),
                                "away_score": goals.get("away"),
                                "timestamp": fixture_data.get("timestamp"),
                                "home_team_id": teams.get("home", {}).get("id"),
                                "away_team_id": teams.get("away", {}).get("id"),
                            }
                            all_fixtures.append(game)
                            
                    elif response.status_code == 429:
                        print(f"  ⚠️ Límite de rate alcanzado en {self.name}")
                        continue
                            
                except Exception as e:
                    print(f"  ⚠️ Error en liga {league_id}: {e}")
                    continue
            
            if all_fixtures:
                print(f"  ✓ API-Football: {len(all_fixtures)} partidos encontrados")
            return all_fixtures
            
        except Exception as e:
            print(f"  ✗ Error en API-Football: {e}")
            return []
    
    def get_team_statistics(self, team_id: int, league_id: int, season: int) -> Optional[Dict]:
        """Obtiene estadísticas detalladas del equipo para la temporada."""
        if not self.enabled or not team_id:
            return None
            
        cache_key = f"{team_id}_{league_id}_{season}"
        if cache_key in self._team_stats_cache:
            return self._team_stats_cache[cache_key]
        
        try:
            headers = {
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": "v3.football.api-sports.io"
            }
            
            url = f"{self.base_url}/teams/statistics"
            params = {
                "team": team_id,
                "league": league_id,
                "season": season
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                stats = data.get("response", {})
                self._team_stats_cache[cache_key] = stats
                return stats
                
        except Exception as e:
            print(f"  ⚠️ Error obteniendo estadísticas del equipo {team_id}: {e}")
        
        return None
    
    def _map_status(self, status_short: str) -> str:
        """Mapea códigos de estado de API-Football a nuestro formato."""
        status_map = {
            "NS": "scheduled",      # Not Started
            "1H": "live",           # First Half
            "HT": "live",           # Halftime
            "2H": "live",           # Second Half
            "ET": "live",           # Extra Time
            "BT": "live",           # Break Time
            "P": "live",            # Penalty
            "SUSP": "suspended",    # Suspended
            "INT": "interrupted",   # Interrupted
            "FT": "finished",       # Match Finished
            "AET": "finished",      # Match Finished After Extra Time
            "PEN": "finished",      # Match Finished After Penalty
            "CANC": "cancelled",    # Cancelled
            "ABD": "abandoned",     # Abandoned
            "AWD": "finished",      # Technical Loss
            "WO": "finished",       # WalkOver
        }
        return status_map.get(status_short, "scheduled")
    
    def get_team_recent_record(self, team_name: str, end_date: date, sport: str = "soccer") -> Dict[str, int]:
        return {'wins': 0, 'losses': 0}


class FootballDataOrgProvider:
    """
    Proveedor usando football-data.org.
    API Key: 16932c5260314df49e05d1ebf00948d9
    """
    
    def __init__(self, api_key: str = None):
        self.name = "Football-Data.org"
        self.base_url = "https://api.football-data.org/v4"
        self.api_key = api_key or DEFAULT_FOOTBALL_DATA_KEY
        self.enabled = bool(self.api_key)
        self._matches_cache = {}
        
    def get_games_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
            
        try:
            headers = {}
            if self.api_key:
                headers["X-Auth-Token"] = self.api_key
            
            # Competiciones principales disponibles
            competitions = [
                "PL",   # Premier League
                "PD",   # La Liga
                "SA",   # Serie A
                "BL1",  # Bundesliga
                "FL1",  # Ligue 1
                "CL",   # Champions League
                "EL",   # Europa League
                "EC",   # Euro Championship
                "WC",   # World Cup
            ]
            
            date_str = target_date.strftime("%Y-%m-%d")
            all_matches = []
            
            for comp in competitions:
                try:
                    url = f"{self.base_url}/competitions/{comp}/matches"
                    params = {"dateFrom": date_str, "dateTo": date_str}
                    
                    response = requests.get(url, headers=headers, params=params, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        matches = data.get("matches", [])
                        
                        for match in matches:
                            status = match.get("status", "")
                            home_team = match.get("homeTeam", {}).get("name")
                            away_team = match.get("awayTeam", {}).get("name")
                            score = match.get("score", {}).get("fullTime", {})
                            
                            # Obtener datos adicionales para predicción
                            home_team_id = match.get("homeTeam", {}).get("id")
                            away_team_id = match.get("awayTeam", {}).get("id")
                            
                            game = {
                                "id": match.get("id"),
                                "home_team": home_team,
                                "away_team": away_team,
                                "status": self._map_status(status),
                                "sport": "soccer",
                                "source": self.name,
                                "league": match.get("competition", {}).get("name"),
                                "home_score": score.get("home"),
                                "away_score": score.get("away"),
                                "utc_date": match.get("utcDate"),
                                "home_team_id": home_team_id,
                                "away_team_id": away_team_id,
                                "matchday": match.get("matchday"),
                            }
                            all_matches.append(game)
                            
                    elif response.status_code == 429:
                        print(f"  ⚠️ Límite de rate alcanzado en {self.name}")
                        continue
                    elif response.status_code == 403:
                        print(f"  ⚠️ Acceso denegado para {comp} (puede requerir plan superior)")
                        continue
                        
                except Exception as e:
                    print(f"  ⚠️ Error en competición {comp}: {e}")
                    continue
            
            if all_matches:
                print(f"  ✓ Football-Data.org: {len(all_matches)} partidos encontrados")
            return all_matches
            
        except Exception as e:
            print(f"  ✗ Error en Football-Data.org: {e}")
            return []
    
    def _map_status(self, status: str) -> str:
        status_map = {
            "SCHEDULED": "scheduled",
            "LIVE": "live",
            "IN_PLAY": "live",
            "PAUSED": "live",
            "FINISHED": "finished",
            "POSTPONED": "postponed",
            "SUSPENDED": "suspended",
            "CANCELLED": "cancelled",
        }
        return status_map.get(status, "scheduled")
    
    def get_team_recent_record(self, team_name: str, end_date: date, sport: str = "soccer") -> Dict[str, int]:
        return {'wins': 0, 'losses': 0}


class AnalistaFutbol:
    """
    Analista que solo analiza partidos de fútbol soccer, consultando directamente
    a múltiples proveedores especializados con fallback automático.
    """

    def __init__(self, api_football_key: str = None, football_data_key: str = None):
        self.nombre = "Analista Fútbol"
        self.api_football_key = api_football_key or DEFAULT_API_FOOTBALL_KEY
        self.football_data_key = football_data_key or DEFAULT_FOOTBALL_DATA_KEY
        
        # Inicializar todos los proveedores disponibles
        self.providers = []
        
        # Proveedores de APIs directas (prioridad alta - más confiables para fixtures)
        self.providers.append(FootballDataOrgProvider(api_key=self.football_data_key))
        self.providers.append(APIFootballProvider(api_key=self.api_football_key))
        
        # Proveedores de data_providers (fallback)
        if PROVIDERS_AVAILABLE:
            self.providers.append(TheSportsDBProvider())
            self.providers.append(OpenLigaDBProvider())
            if ENABLE_BBC_SPORT:
                try:
                    self.providers.append(BBCSportProvider())
                except Exception as e:
                    print(f"  ⚠️ BBC Sport no disponible: {e}")

    def _obtener_juegos_futbol(self, fecha: date) -> List[Dict[str, Any]]:
        """
        Consulta secuencialmente los proveedores de fútbol y combina los juegos.
        Implementa lógica de deduplicación y filtrado de ligas relevantes.
        """
        juegos = []
        juegos_ids = set()  # Para evitar duplicados
        
        # Ligas/soccer que queremos (filtrar fútbol americano, etc.)
        ligas_validas = [
            "premier league", "la liga", "serie a", "bundesliga", "ligue 1",
            "champions league", "europa league", "liga mx", "brasileirão",
            "primera división", "eredivisie", "primeira liga", "premiership",
            "major league soccer", "mls", "j1 league", "k league", "liga portugal"
        ]
        
        for provider in self.providers:
            print(f"  Intentando obtener datos de fútbol desde {provider.name}...")
            try:
                datos = provider.get_games_by_date(fecha)
                if datos:
                    juegos_validos = []
                    for j in datos:
                        # Verificar que sea fútbol soccer (no americano, australiano, etc.)
                        home = str(j.get("home_team", "")).lower()
                        away = str(j.get("away_team", "")).lower()
                        league = str(j.get("league", "")).lower() if j.get("league") else ""
                        
                        # Filtrar fútbol americano por palabras clave
                        es_futbol_americano = any(word in home or word in away for word in 
                            ["nfl", "ncaa", "college football", "gridiron", "cfl"])
                        
                        # Si parece fútbol americano y no está en ligas válidas, saltar
                        if es_futbol_americano and not any(liga in league for liga in ligas_validas):
                            continue
                        
                        # También filtrar por nombres de equipos universitarios de fútbol americano
                        equipos_futbol_americano = [
                            "unlv", "fresno state", "stanford", "washington state",
                            "alabama", "ohio state", "clemson", "notre dame",
                            "usc", "ucla", "texas", "oklahoma", "georgia",
                            "florida", "michigan", "penn state", "lsu", "auburn",
                            "tennessee", "oregon", "utah", "colorado", "arizona",
                            "arizona state", "california", "oregon state", "washington",
                            "boise state", "san diego state", "nevada", "hawaii",
                            "new mexico", "san jose state", "wyoming", "air force",
                            "army", "navy", "troy", "appalachian state"
                        ]
                        
                        if any(team in home or team in away for team in equipos_futbol_americano):
                            if not any(liga in league for liga in ligas_validas):
                                continue
                        
                        # Crear ID único para deduplicación
                        game_id = f"{home}_{away}_{fecha.isoformat()}"
                        
                        if game_id not in juegos_ids:
                            juegos_ids.add(game_id)
                            # Asegurar que tenga campo sport
                            j["sport"] = "soccer"
                            juegos_validos.append(j)
                    
                    if juegos_validos:
                        print(f"  ✓ {provider.name}: {len(juegos_validos)} partidos válidos añadidos.")
                        juegos.extend(juegos_validos)
                    else:
                        print(f"  ✗ {provider.name}: No hay partidos válidos de fútbol soccer.")
                else:
                    print(f"  ✗ {provider.name}: No devolvió datos.")
                    
            except Exception as e:
                print(f"  ✗ Error en {provider.name}: {e}")
                continue
        
        return juegos

    def _obtener_datos_rendimiento(self, team_name: str, fecha: date) -> Dict[str, Any]:
        """
        Obtiene datos de rendimiento del equipo (últimos 5 y 14 días).
        """
        if data_manager:
            record_14 = data_manager.get_team_recent_record(team_name, fecha, "soccer")
        else:
            record_14 = {'wins': 0, 'losses': 0}
        
        # Calcular últimos 5 días manualmente
        start_5 = fecha - timedelta(days=5)
        wins_5 = 0
        losses_5 = 0
        draws_5 = 0  # Importante en fútbol
        total_goals_for = 0
        total_goals_against = 0
        games_5 = 0

        if data_manager:
            current_date = start_5
            while current_date <= fecha:
                try:
                    juegos = data_manager.get_games_by_date(current_date)
                    for juego in juegos:
                        if juego.get("sport") != "soccer":
                            continue
                        if juego.get("home_team") == team_name or juego.get("away_team") == team_name:
                            if juego.get("status") not in ["finished", "post", "final", "FT", "AET", "PEN"]:
                                continue
                            
                            home_score = juego.get("home_score")
                            away_score = juego.get("away_score")
                            if home_score is None or away_score is None:
                                continue
                            
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
                            elif team_score < opp_score:
                                losses_5 += 1
                            else:
                                draws_5 += 1
                                
                            total_goals_for += team_score
                            total_goals_against += opp_score
                            games_5 += 1
                            
                except Exception:
                    pass
                current_date += timedelta(days=1)

        avg_for = total_goals_for / games_5 if games_5 > 0 else None
        avg_against = total_goals_against / games_5 if games_5 > 0 else None

        return {
            'wins_14': record_14.get('wins', 0),
            'losses_14': record_14.get('losses', 0),
            'wins_5': wins_5,
            'losses_5': losses_5,
            'draws_5': draws_5,
            'avg_goals_for': avg_for,
            'avg_goals_against': avg_against,
            'games_5': games_5
        }

    def _calcular_probabilidad_mejorada(self, local_data: Dict, visitante_data: Dict, 
                                        home_name: str, away_name: str) -> Tuple[float, Dict[str, Any]]:
        """
        Modelo mejorado de probabilidad con múltiples factores y cálculo de xG (expected goals).
        Retorna: (probabilidad_local, datos_extendidos)
        """
        # Factores base
        def win_pct(w, l, d=0):
            total = w + l + d
            if total == 0:
                return None
            return w / total

        # Calcular porcentajes de victoria
        pct14_local = win_pct(local_data['wins_14'], local_data['losses_14'])
        pct14_visit = win_pct(visitante_data['wins_14'], visitante_data['losses_14'])
        
        # Si no hay datos históricos, usar valores por defecto basados en la liga
        if pct14_local is None:
            pct14_local = 0.45  # Ligeramente menor por ser local (más presión)
        if pct14_visit is None:
            pct14_visit = 0.35  # Menor por ser visitante
        
        # Forma reciente (últimos 5) con peso mayor
        total_5_local = local_data['wins_5'] + local_data['losses_5'] + local_data.get('draws_5', 0)
        total_5_visit = visitante_data['wins_5'] + visitante_data['losses_5'] + visitante_data.get('draws_5', 0)
        
        if total_5_local > 0:
            # Ponderar victorias (1.0), empates (0.5), derrotas (0.0)
            forma_local = (local_data['wins_5'] * 1.0 + local_data.get('draws_5', 0) * 0.5) / total_5_local
        else:
            forma_local = 0.5
            
        if total_5_visit > 0:
            forma_visit = (visitante_data['wins_5'] + visitante_data.get('draws_5', 0) * 0.5) / total_5_visit
        else:
            forma_visit = 0.5

        # Diferencia de goles esperados (xG aproximado)
        # Usar promedios de goles si están disponibles, si no usar estimaciones de la liga
        avg_goals_local = local_data.get('avg_goals_for') or 1.4  # Promedio general de fútbol
        avg_goals_against_local = local_data.get('avg_goals_against') or 1.2
        avg_goals_visit = visitante_data.get('avg_goals_for') or 1.1  # Menor por ser visitante
        avg_goals_against_visit = visitante_data.get('avg_goals_against') or 1.3
        
        # Calcular xG aproximado para cada equipo
        # Fórmula: xG = (promedio goles a favor local + promedio goles en contra visitante) / 2
        xg_local = (avg_goals_local + avg_goals_against_visit) / 2
        xg_visit = (avg_goals_visit + avg_goals_against_local) / 2
        
        # Ajustar por localía
        xg_local *= 1.15  # +15% por jugar en casa
        xg_visit *= 0.90  # -10% por jugar fuera
        
        # Modelo de probabilidad basado en xG (modelo de Poisson simplificado)
        # P(local gana) ≈ P(local marca más que visitante)
        from math import exp
        
        def poisson_prob(lambda_, k):
            """Probabilidad de Poisson P(X=k)"""
            return (lambda_ ** k) * exp(-lambda_) / self._factorial(k)
        
        # Calcular probabilidades de resultado
        prob_local_wins = 0
        prob_draw = 0
        prob_visit_wins = 0
        
        # Simular hasta 5 goles para cada equipo
        for g_local in range(6):
            for g_visit in range(6):
                p = poisson_prob(xg_local, g_local) * poisson_prob(xg_visit, g_visit)
                if g_local > g_visit:
                    prob_local_wins += p
                elif g_local == g_visit:
                    prob_draw += p
                else:
                    prob_visit_wins += p
        
        # Combinar con factores de forma (peso 60% xG, 40% forma)
        prob_local_xg = prob_local_wins + (prob_draw * 0.5)  # Mitad de los empates para local
        prob_visit_xg = prob_visit_wins + (prob_draw * 0.5)
        
        # Normalizar
        total_xg = prob_local_xg + prob_visit_xg
        if total_xg > 0:
            prob_local_xg /= total_xg
            prob_visit_xg /= total_xg
        
        # Combinar con forma reciente
        forma_diff = forma_local - forma_visit
        forma_factor = forma_diff * 0.20  # ±20% máximo por forma
        
        prob_local = prob_local_xg + forma_factor
        prob_local = max(0.15, min(0.85, prob_local))  # Limitar extremos
        
        # Datos extendidos para el comentario y predicción de marcador
        datos_extendidos = {
            'xg_local': xg_local,
            'xg_visit': xg_visit,
            'prob_local_wins': prob_local_wins,
            'prob_draw': prob_draw,
            'prob_visit_wins': prob_visit_wins,
            'forma_local': forma_local,
            'forma_visit': forma_visit,
            'avg_goals_local': avg_goals_local,
            'avg_goals_visit': avg_goals_visit,
            'pct14_local': pct14_local,
            'pct14_visit': pct14_visit,
        }
        
        return prob_local, datos_extendidos
    
    def _factorial(self, n: int) -> int:
        """Calcula factorial de n."""
        if n <= 1:
            return 1
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result

    def _predecir_marcador(self, xg_local: float, xg_visit: float) -> Tuple[int, int]:
        """
        Predice el marcador más probable basado en xG.
        Usa el valor esperado redondeado, con variación según la confianza.
        """
        # Marcador base (valor esperado redondeado)
        goles_local = round(xg_local)
        goles_visit = round(xg_visit)
        
        # Ajustar para evitar 0-0 muy frecuente
        if goles_local == 0 and goles_visit == 0:
            # Si ambos xG > 0.5, forzar al menos 1 gol en el que tenga mayor xG
            if xg_local > xg_visit and xg_local > 0.6:
                goles_local = 1
            elif xg_visit > xg_local and xg_visit > 0.6:
                goles_visit = 1
        
        # Variación aleatoria controlada (±1 gol) basada en la diferencia de xG
        diff_xg = abs(xg_local - xg_visit)
        if diff_xg > 1.0:
            # Si hay diferencia clara, el favorito tiene más probabilidad de marcar más
            if xg_local > xg_visit:
                goles_local = max(goles_local, 1)
            else:
                goles_visit = max(goles_visit, 1)
        
        return goles_local, goles_visit

    def _generar_comentario_mejorado(self, local_data: Dict, visitante_data: Dict,
                                      home_name: str, away_name: str, prob_local: float,
                                      datos_extendidos: Dict[str, Any], 
                                      marcador_predicho: Tuple[int, int]) -> str:
        """
        Genera un comentario detallado con análisis del marcador y factores clave.
        """
        xg_local = datos_extendidos['xg_local']
        xg_visit = datos_extendidos['xg_visit']
        prob_local_wins = datos_extendidos['prob_local_wins']
        prob_draw = datos_extendidos['prob_draw']
        prob_visit_wins = datos_extendidos['prob_visit_wins']
        forma_local = datos_extendidos['forma_local']
        forma_visit = datos_extendidos['forma_visit']
        
        goles_local, goles_visit = marcador_predicho
        
        # Determinar resultado más probable
        if prob_local > 0.55:
            resultado = "VICTORIA LOCAL"
            emoji = "🏠"
        elif prob_local < 0.45:
            resultado = "VICTORIA VISITANTE"
            emoji = "✈️"
        else:
            resultado = "EMPATE O RESULTADO MUY PAREJO"
            emoji = "⚖️"
        
        prob_ganar = max(prob_local, 1 - prob_local)
        
        comentario = f"{emoji} PREDICCIÓN: {resultado}\n"
        comentario += f"📊 Probabilidad: {prob_ganar*100:.1f}%\n"
        comentario += f"⚽ Marcador estimado: {home_name} {goles_local} - {goles_visit} {away_name}\n\n"
        
        comentario += "📈 ANÁLISIS DETALLADO:\n"
        comentario += f"• Goles esperados (xG): {home_name} {xg_local:.2f} vs {away_name} {xg_visit:.2f}\n"
        comentario += f"• Probabilidades de resultado:\n"
        comentario += f"  - Victoria {home_name}: {prob_local_wins*100:.1f}%\n"
        comentario += f"  - Empate: {prob_draw*100:.1f}%\n"
        comentario += f"  - Victoria {away_name}: {prob_visit_wins*100:.1f}%\n\n"
        
        # Forma reciente
        comentario += "🔥 FORMA RECIENTE (últimos 5 partidos):\n"
        total_5_local = local_data['wins_5'] + local_data['losses_5'] + local_data.get('draws_5', 0)
        total_5_visit = visitante_data['wins_5'] + visitante_data['losses_5'] + visitante_data.get('draws_5', 0)
        
        if total_5_local > 0:
            comentario += f"  {home_name}: {local_data['wins_5']}V {local_data.get('draws_5', 0)}E {local_data['losses_5']}D "
            comentario += f"(efectividad: {forma_local*100:.0f}%)\n"
        else:
            comentario += f"  {home_name}: Sin datos recientes disponibles\n"
            
        if total_5_visit > 0:
            comentario += f"  {away_name}: {visitante_data['wins_5']}V {visitante_data.get('draws_5', 0)}E {visitante_data['losses_5']}D "
            comentario += f"(efectividad: {forma_visit*100:.0f}%)\n"
        else:
            comentario += f"  {away_name}: Sin datos recientes disponibles\n"
        
        # Estadísticas de goles
        if local_data['avg_goals_for'] is not None or visitante_data['avg_goals_for'] is not None:
            comentario += "\n⚽ PROMEDIO DE GOLES:\n"
            if local_data['avg_goals_for'] is not None:
                comentario += f"  {home_name}: {local_data['avg_goals_for']:.2f} GF / {local_data['avg_goals_against']:.2f} GC\n"
            if visitante_data['avg_goals_for'] is not None:
                comentario += f"  {away_name}: {visitante_data['avg_goals_for']:.2f} GF / {visitante_data['avg_goals_against']:.2f} GC\n"
        
        # Análisis de confianza y recomendación
        comentario += "\n💡 RECOMENDACIÓN:\n"
        if prob_ganar > 0.70:
            comentario += "✅ ALTA CONFIANZA: El modelo indica ventaja significativa.\n"
            if prob_draw > 0.25:
                comentario += "⚠️ Considerar cobertura del empate (Draw No Bet).\n"
        elif prob_ganar > 0.60:
            comentario += "⚠️ CONFIANZA MEDIA: Ventaja detectada pero no decisiva.\n"
            comentario += "💡 Sugerencia: Apostar con stake moderado o buscar handicap.\n"
        else:
            comentario += "❌ BAJA CONFIANZA: Partido muy equilibrado.\n"
            comentario += "💡 Sugerencia: Evitar apuesta directa, considerar ambos marcan o over/under.\n"
        
        # Over/under basado en xG total
        xg_total = xg_local + xg_visit
        comentario += f"\n📊 MERCADOS ALTERNATIVOS:\n"
        if xg_total > 2.5:
            comentario += f"• Over 2.5 goles: Probable (xG total: {xg_total:.2f})\n"
        elif xg_total > 1.8:
            comentario += f"• Over/Under 2.5: Equilibrado (xG total: {xg_total:.2f})\n"
        else:
            comentario += f"• Under 2.5 goles: Probable (xG total: {xg_total:.2f})\n"
        
        if prob_draw > 0.28:
            comentario += f"• Empate tiene valor: {prob_draw*100:.1f}% de probabilidad\n"
        
        return comentario

    def analizar_juegos_dia(self, fecha: date) -> List[Prediccion]:
        """
        Analiza solo los partidos de fútbol del día con modelo mejorado de predicción.
        """
        print(f"\n--- {self.nombre} analizando juegos de fútbol para {fecha} ---")

        # Obtener juegos de fútbol de múltiples fuentes
        juegos = self._obtener_juegos_futbol(fecha)

        if not juegos:
            print("❌ No se encontraron partidos de fútbol para hoy en ninguna fuente.")
            print("💡 Sugerencias:")
            print("   - Verifica tu conexión a internet")
            print("   - Las APIs pueden estar en mantenimiento")
            print("   - Intenta más tarde (las APIs tienen límites de rate)")
            return []

        print(f"\n📊 Total de partidos únicos encontrados: {len(juegos)}")

        # Filtrar solo los que no han finalizado y son hoy o futuro
        juegos_programados = []
        hoy = date.today()
        
        for j in juegos:
            status = j.get("status", "").lower()
            
            # Estados que indican partido jugable
            estados_validos = ["scheduled", "ns", "not started", "timed", "upcoming", "postponed"]
            estados_invalidos = ["finished", "ft", "final", "completed", "cancelled", "abandoned", "suspended"]
            
            # Verificar fecha si está disponible
            fecha_partido = None
            if j.get("timestamp"):
                try:
                    fecha_partido = datetime.fromtimestamp(j["timestamp"]).date()
                except:
                    pass
            elif j.get("utc_date"):
                try:
                    fecha_partido = datetime.fromisoformat(j["utc_date"].replace('Z', '+00:00')).date()
                except:
                    pass
            
            # Incluir si no ha finalizado y es hoy o futuro (con margen de 1 día por zonas horarias)
            if status not in estados_invalidos:
                if fecha_partido is None or fecha_partido >= hoy - timedelta(days=1):
                    juegos_programados.append(j)

        if not juegos_programados:
            print(f"⚠️ Se encontraron {len(juegos)} partidos, pero todos ya han finalizado o no son programables.")
            print("\nEstados de los primeros 5 partidos encontrados:")
            for j in juegos[:5]:
                print(f"  • {j.get('home_team')} vs {j.get('away_team')} - Estado: {j.get('status')} - Liga: {j.get('league', 'N/A')}")
            return []

        print(f"✅ {len(juegos_programados)} partidos programados para hoy o próximos días.")

        predicciones = []
        for juego in juegos_programados:
            home_name = juego.get("home_team", "")
            away_name = juego.get("away_team", "")
            
            if not home_name or not away_name:
                continue
            
            # Limpiar nombres
            home_name = str(home_name).strip()
            away_name = str(away_name).strip()

            print(f"\n  ⚽ Analizando: {home_name} vs {away_name}")
            if juego.get("league"):
                print(f"     Liga: {juego['league']}")

            try:
                # Obtener datos de rendimiento
                local_data = self._obtener_datos_rendimiento(home_name, fecha)
                visitante_data = self._obtener_datos_rendimiento(away_name, fecha)

                # Usar el modelo mejorado de probabilidad
                prob_local, datos_extendidos = self._calcular_probabilidad_mejorada(
                    local_data, visitante_data, home_name, away_name
                )
                
                prob = max(prob_local, 1 - prob_local)
                ganador = home_name if prob_local > 0.5 else away_name

                # Predecir marcador
                marcador_predicho = self._predecir_marcador(
                    datos_extendidos['xg_local'], 
                    datos_extendidos['xg_visit']
                )
                goles_local, goles_visit = marcador_predicho
                marcador_str = f"{goles_local}-{goles_visit}"

                if prob < UMBRAL_PROBABILIDAD:
                    print(f"     ⏭️ Omitido: probabilidad {prob*100:.1f}% < {UMBRAL_PROBABILIDAD*100:.0f}%")
                    print(f"        Marcador estimado: {marcador_str}")
                    continue

                # Generar comentario mejorado
                comentario = self._generar_comentario_mejorado(
                    local_data, visitante_data,
                    home_name, away_name, prob_local,
                    datos_extendidos, marcador_predicho
                )

                pred = Prediccion(
                    fecha=fecha,
                    equipo_local=home_name,
                    equipo_visitante=away_name,
                    ganador_predicho=ganador,
                    probabilidad=prob,
                    deporte="⚽ FÚTBOL",
                    marcador_estimado=marcador_str,
                    comentario=comentario,
                    analista=self.nombre
                )
                predicciones.append(pred)
                print(f"     ✅ Predicción: {ganador} ({prob*100:.1f}%) - Marcador: {marcador_str}")

            except Exception as e:
                print(f"     ❌ Error analizando partido: {e}")
                import traceback
                traceback.print_exc()
                continue

        # Ordenar de mayor a menor probabilidad
        predicciones.sort(key=lambda p: p.probabilidad, reverse=True)
        
        print(f"\n{'='*70}")
        if len(predicciones) == 0:
            print(f"📉 {self.nombre}: No hay partidos con probabilidad ≥ {UMBRAL_PROBABILIDAD*100:.0f}%")
            print(f"\n💡 CONSEJO: Prueba reducir el umbral en config.py (actual: {UMBRAL_PROBABILIDAD*100:.0f}%)")
            print(f"   o busca valor en mercados alternativos como ambos marcan o over/under.")
        elif len(predicciones) < 3:
            print(f"⚠️ {self.nombre}: Solo {len(predicciones)} partido(s) con prob ≥ {UMBRAL_PROBABILIDAD*100:.0f}%.")
        else:
            print(f"✅ {self.nombre}: {len(predicciones)} partidos con alta probabilidad.")
        
        # Mostrar resumen de predicciones
        if predicciones:
            print(f"\n📋 RESUMEN DE PREDICCIONES:")
            for i, pred in enumerate(predicciones, 1):
                marcador_info = f" | Marcador: {pred.marcador_estimado}" if pred.marcador_estimado else ""
                print(f"   {i}. {pred.equipo_local} vs {pred.equipo_visitante} → {pred.ganador_predicho} ({pred.probabilidad*100:.1f}%){marcador_info}")
        
        print(f"{'='*70}")
        return predicciones