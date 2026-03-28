# data_providers.py
"""
Módulo para manejar múltiples fuentes de datos deportivos con fallback automático.
Incluye proveedores para:
- sports-skills (MLB, NFL, NBA, NHL, fútbol)
- ESPN (scoreboards)
- balldontlie (NBA con API key)
- OpenLigaDB (fútbol alemán)
- DraftKings (cuotas)
- TheSportsDB (múltiples deportes)
- NBA Data (data.nba.com)
- NHL Stats API (statsapi.web.nhl.com)
- BBC Sport (fútbol, scraping con Selenium)
"""

import requests
import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from config import BALDONTLIE_API_KEY, ENABLE_BBC_SPORT, BBC_HEADLESS, BBC_TIMEOUT

# Intentar importar sports-skills
try:
    from sports_skills import mlb as mlb_skill
    from sports_skills import nfl as nfl_skill
    from sports_skills import nba as nba_skill
    SPORTS_SKILLS_AVAILABLE = True
except ImportError:
    SPORTS_SKILLS_AVAILABLE = False
    print("Nota: sports-skills no instalado. Para mejor cobertura: pip install sports-skills")

DIAS_HISTORICO_RECIENTE = 14


class BaseDataProvider:
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self.failure_count = 0
        self.last_failure_time = None

    def get_games_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get_game_result(self, game_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    def get_team_stats(self, team_name: str, date: date, sport: str = "mlb") -> Optional['TeamStats']:
        return None

    def get_team_recent_record(self, team_name: str, end_date: date, sport: str = "mlb") -> Dict[str, int]:
        return {'wins': 0, 'losses': 0}

    def mark_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()

    def mark_success(self):
        self.failure_count = 0


class SportsSkillsProvider(BaseDataProvider):
    def __init__(self):
        super().__init__("sports-skills")
        self.mlb_skill = mlb_skill if SPORTS_SKILLS_AVAILABLE else None

    def get_games_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        if not SPORTS_SKILLS_AVAILABLE or not self.mlb_skill:
            return []
        try:
            date_str = target_date.strftime("%Y-%m-%d")
            result = self.mlb_skill.get_scoreboard(date=date_str)
            if result and isinstance(result, dict):
                events = result.get("data", {}).get("events")
                if not events:
                    events = result.get("events")
                if events and isinstance(events, list):
                    games = []
                    for event in events:
                        try:
                            comp = event.get("competitions", [{}])[0]
                            comps = comp.get("competitors", [])
                            if len(comps) >= 2:
                                game = {
                                    "id": event.get("id"),
                                    "home_team": comps[0].get("team", {}).get("name"),
                                    "away_team": comps[1].get("team", {}).get("name"),
                                    "status": event.get("status", {}).get("type", {}).get("state"),
                                    "source": self.name,
                                    "sport": "mlb"
                                }
                                games.append(game)
                        except (IndexError, KeyError, TypeError):
                            continue
                    if games:
                        return games
        except Exception as e:
            pass
        return []

    def get_team_stats(self, team_name: str, date: date, sport: str = "mlb") -> Optional['TeamStats']:
        return None

    def get_team_recent_record(self, team_name: str, end_date: date, sport: str = "mlb") -> Dict[str, int]:
        return {'wins': 0, 'losses': 0}


class ESPNProvider(BaseDataProvider):
    def __init__(self):
        super().__init__("ESPN")
        self.base_url = "https://site.web.api.espn.com/apis/site/v2/sports"
        self._games_cache = {}

    def get_games_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        games = []
        date_param = target_date.strftime("%Y%m%d")
        params = {"dates": date_param, "region": "us", "lang": "en"}

        sports = {
            "baseball/mlb": "mlb",
            "football/nfl": "nfl",
            "basketball/nba": "nba",
            "hockey/nhl": "nhl"
        }
        for sport_path, sport_code in sports.items():
            try:
                url = f"{self.base_url}/{sport_path}/scoreboard"
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                if data.get("events"):
                    for event in data["events"]:
                        try:
                            comps = event.get("competitions", [{}])[0].get("competitors", [])
                            if len(comps) >= 2:
                                game = {
                                    "id": event.get("id"),
                                    "home_team": comps[0].get("team", {}).get("displayName"),
                                    "away_team": comps[1].get("team", {}).get("displayName"),
                                    "status": event.get("status", {}).get("type", {}).get("state"),
                                    "sport": sport_code,
                                    "source": self.name
                                }
                                if event.get("status", {}).get("type", {}).get("state") == "post":
                                    game["home_score"] = comps[0].get("score")
                                    game["away_score"] = comps[1].get("score")
                                games.append(game)
                        except (IndexError, KeyError):
                            continue
            except requests.exceptions.RequestException as e:
                continue

        if games:
            self.mark_success()
        else:
            self.mark_failure()
        self._games_cache[target_date] = games
        return games

    def get_team_recent_record(self, team_name: str, end_date: date, sport: str = "mlb") -> Dict[str, int]:
        start_date = end_date - timedelta(days=DIAS_HISTORICO_RECIENTE)
        wins = 0
        losses = 0
        current_date = start_date
        while current_date <= end_date:
            if current_date not in self._games_cache:
                self.get_games_by_date(current_date)
            games = self._games_cache.get(current_date, [])
            for game in games:
                if game.get("sport") != sport:
                    continue
                if game["home_team"] == team_name or game["away_team"] == team_name:
                    if game["status"] != "post":
                        continue
                    home_score = game.get("home_score")
                    away_score = game.get("away_score")
                    if home_score is None or away_score is None:
                        continue
                    is_home = (game["home_team"] == team_name)
                    team_score = home_score if is_home else away_score
                    opp_score = away_score if is_home else home_score
                    if team_score > opp_score:
                        wins += 1
                    else:
                        losses += 1
            current_date += timedelta(days=1)
        return {'wins': wins, 'losses': losses}

    def get_game_result(self, game_id: str) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/baseball/mlb/summary"
            params = {"event": game_id, "region": "us", "lang": "en"}
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            if data.get("boxscore", {}).get("teams"):
                teams = data["boxscore"]["teams"]
                return {
                    "home_score": teams[0].get("statistics", [{}])[0].get("displayValue") if teams else None,
                    "away_score": teams[1].get("statistics", [{}])[0].get("displayValue") if len(teams) > 1 else None,
                    "winner": teams[0].get("team", {}).get("displayName") if teams[0].get("homeAway") == "home" else teams[1].get("team", {}).get("displayName")
                }
        except Exception as e:
            print(f"Error obteniendo resultado de ESPN: {e}")
        return {}


class OpenLigaDBProvider(BaseDataProvider):
    def __init__(self):
        super().__init__("OpenLigaDB")
        self.base_url = "https://www.openligadb.de/api"
        self.leagues = ["bl1", "bl2", "bl3"]
        self._games_cache = {}

    def get_games_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        games = []
        # Calcular temporada: normalmente el año de inicio de la temporada
        # Para la temporada 2025-2026, el año es 2025. Pero si estamos en marzo 2026,
        # podemos probar con 2025 y si falla, probar con 2026 (aunque sería inusual).
        # En lugar de complicar, usamos el año actual restando 1 si es antes de agosto.
        # Pero para marzo 2026, estamos después de agosto 2025, entonces la temporada es 2025.
        # Si falla, podemos probar con 2026 como respaldo.
        season = target_date.year
        if target_date.month < 7:
            season = season - 1  # Estamos en la primera mitad del año, la temporada empezó el año anterior
        # Intentamos con season; si falla, probamos con season+1
        seasons_to_try = [season]
        if target_date.month >= 7:
            seasons_to_try.append(season+1)  # para casos de transición

        for league in self.leagues:
            for s in seasons_to_try:
                try:
                    url = f"{self.base_url}/getmatches/{league}/{s}"
                    response = requests.get(url, timeout=10)
                    if response.status_code == 404:
                        continue  # probar la siguiente temporada
                    response.raise_for_status()
                    data = response.json()
                    for match in data:
                        try:
                            match_date = datetime.fromisoformat(match.get("matchDateTime", "")).date()
                            if match_date == target_date:
                                game = {
                                    "id": match.get("matchID"),
                                    "home_team": match.get("team1", {}).get("teamName"),
                                    "away_team": match.get("team2", {}).get("teamName"),
                                    "status": "finished" if match.get("matchIsFinished") else "scheduled",
                                    "league": league,
                                    "sport": "soccer",
                                    "source": self.name
                                }
                                if match.get("matchIsFinished"):
                                    game["home_score"] = match.get("matchResults", [{}])[0].get("pointsTeam1")
                                    game["away_score"] = match.get("matchResults", [{}])[0].get("pointsTeam2")
                                games.append(game)
                        except (KeyError, IndexError, TypeError):
                            continue
                    if games:
                        break  # si encontramos partidos, salir del bucle de temporadas
                except Exception as e:
                    print(f"Error en OpenLigaDB para {league}, temporada {s}: {e}")
                    continue
        if games:
            self.mark_success()
        else:
            self.mark_failure()
        self._games_cache[target_date] = games
        return games

    def get_team_recent_record(self, team_name: str, end_date: date, sport: str = "soccer") -> Dict[str, int]:
        if sport != "soccer":
            return {'wins': 0, 'losses': 0}
        start_date = end_date - timedelta(days=DIAS_HISTORICO_RECIENTE)
        wins = 0
        losses = 0
        current_date = start_date
        while current_date <= end_date:
            if current_date not in self._games_cache:
                self.get_games_by_date(current_date)
            games = self._games_cache.get(current_date, [])
            for game in games:
                if game["home_team"] == team_name or game["away_team"] == team_name:
                    if game["status"] != "finished":
                        continue
                    home_score = game.get("home_score")
                    away_score = game.get("away_score")
                    if home_score is None or away_score is None:
                        continue
                    is_home = (game["home_team"] == team_name)
                    team_score = home_score if is_home else away_score
                    opp_score = away_score if is_home else home_score
                    if team_score > opp_score:
                        wins += 1
                    else:
                        losses += 1
            current_date += timedelta(days=1)
        return {'wins': wins, 'losses': losses}

    def get_game_result(self, game_id: str) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/getmatchdata/{game_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("matchIsFinished"):
                return {
                    "home_score": data.get("matchResults", [{}])[0].get("pointsTeam1") if data.get("matchResults") else None,
                    "away_score": data.get("matchResults", [{}])[0].get("pointsTeam2") if data.get("matchResults") else None,
                    "winner": data.get("team1", {}).get("teamName") if data.get("matchResults", [{}])[0].get("pointsTeam1", 0) > data.get("matchResults", [{}])[0].get("pointsTeam2", 0) else data.get("team2", {}).get("teamName")
                }
        except Exception as e:
            print(f"Error obteniendo resultado de OpenLigaDB: {e}")
        return {}


class DraftKingsProvider(BaseDataProvider):
    def __init__(self):
        super().__init__("DraftKings")
        self.base_url = "https://api.draftkings.com"

    def get_games_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        try:
            sports_url = f"{self.base_url}/sites/US-DK/sports/v1/sports?format=json"
            response = requests.get(sports_url, timeout=10)
            response.raise_for_status()
            sports = response.json().get("sports", [])
            games = []
            target_date_str = target_date.strftime("%Y-%m-%d")
            for sport in sports:
                sport_name = sport.get("name")
                contests_url = f"https://www.draftkings.com/lobby/getcontests?sport={sport_name}"
                response = requests.get(contests_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    for contest in data.get("contests", []):
                        if contest.get("startDate", "").startswith(target_date_str):
                            contest_name = contest.get("name", "")
                            game = {
                                "id": contest.get("id"),
                                "home_team": contest_name.split(" vs ")[0] if " vs " in contest_name else contest_name,
                                "away_team": contest_name.split(" vs ")[1] if " vs " in contest_name else "",
                                "status": "scheduled",
                                "sport": sport_name,
                                "source": self.name
                            }
                            games.append(game)
            if games:
                self.mark_success()
            else:
                self.mark_failure()
            return games
        except Exception as e:
            print(f"Error en DraftKingsProvider: {e}")
            self.mark_failure()
            return []

    def get_team_recent_record(self, team_name: str, end_date: date, sport: str = "mlb") -> Dict[str, int]:
        return {'wins': 0, 'losses': 0}


class BallDontLieProvider(BaseDataProvider):
    def __init__(self):
        super().__init__("balldontlie")
        self.base_url = "https://www.balldontlie.io/api/v1"
        self.api_key = BALDONTLIE_API_KEY
        self._games_cache = {}

    def _get_headers(self):
        return {"Authorization": self.api_key} if self.api_key else {}

    def _has_data_for_date(self, target_date: date) -> bool:
        return target_date <= date.today()

    def get_games_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        if not self._has_data_for_date(target_date):
            return []
        try:
            date_str = target_date.strftime("%Y-%m-%d")
            url = f"{self.base_url}/games"
            params = {"dates[]": date_str}
            headers = self._get_headers()
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            data = response.json()
            games = []
            for game in data.get("data", []):
                game_info = {
                    "id": game.get("id"),
                    "home_team": game.get("home_team", {}).get("full_name"),
                    "away_team": game.get("visitor_team", {}).get("full_name"),
                    "home_score": game.get("home_team_score"),
                    "away_score": game.get("visitor_team_score"),
                    "status": "finished" if game.get("status") == "Final" else "scheduled",
                    "date": game.get("date"),
                    "sport": "basketball",
                    "source": self.name
                }
                games.append(game_info)
            if games:
                self.mark_success()
            else:
                self.mark_failure()
            self._games_cache[target_date] = games
            return games
        except Exception as e:
            print(f"Error en BallDontLieProvider: {e}")
            self.mark_failure()
            return []

    def get_team_recent_record(self, team_name: str, end_date: date, sport: str = "basketball") -> Dict[str, int]:
        if sport != "basketball":
            return {'wins': 0, 'losses': 0}
        if not self._has_data_for_date(end_date):
            return {'wins': 0, 'losses': 0}
        start_date = end_date - timedelta(days=DIAS_HISTORICO_RECIENTE)
        wins = 0
        losses = 0
        current_date = start_date
        while current_date <= end_date:
            if not self._has_data_for_date(current_date):
                current_date += timedelta(days=1)
                continue
            if current_date not in self._games_cache:
                self.get_games_by_date(current_date)
            games = self._games_cache.get(current_date, [])
            for game in games:
                if game["home_team"] == team_name or game["away_team"] == team_name:
                    if game["status"] != "finished":
                        continue
                    home_score = game.get("home_score")
                    away_score = game.get("away_score")
                    if home_score is None or away_score is None:
                        continue
                    is_home = (game["home_team"] == team_name)
                    team_score = home_score if is_home else away_score
                    opp_score = away_score if is_home else home_score
                    if team_score > opp_score:
                        wins += 1
                    else:
                        losses += 1
            current_date += timedelta(days=1)
        return {'wins': wins, 'losses': losses}

    def get_team_stats(self, team_name: str, date: date, sport: str = "basketball") -> Optional['TeamStats']:
        if sport != "basketball":
            return None
        if not self._has_data_for_date(date):
            return None
        try:
            url = f"{self.base_url}/teams"
            headers = self._get_headers()
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            teams = response.json().get("data", [])
            team_id = None
            for team in teams:
                if team.get("full_name", "").lower() == team_name.lower():
                    team_id = team.get("id")
                    break
            if not team_id:
                return None
            end_date = date
            start_date = end_date - timedelta(days=30)
            params = {
                "team_ids[]": team_id,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "per_page": 10
            }
            url = f"{self.base_url}/games"
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            games = response.json().get("data", [])
            if not games:
                return None
            total_points = 0
            total_opp_points = 0
            total_games = 0
            for game in games:
                if game.get("home_team_id") == team_id:
                    points = game.get("home_team_score")
                    opp_points = game.get("visitor_team_score")
                elif game.get("visitor_team_id") == team_id:
                    points = game.get("visitor_team_score")
                    opp_points = game.get("home_team_score")
                else:
                    continue
                total_points += points
                total_opp_points += opp_points
                total_games += 1
            if total_games == 0:
                return None
            avg_pts = total_points / total_games
            avg_opp_pts = total_opp_points / total_games
            from statistics import TeamStats
            stats = TeamStats(sport="basketball")
            stats.off_rating = avg_pts
            stats.def_rating = avg_opp_pts
            stats.ts_percent = 0.55
            stats.efg_percent = 0.52
            stats.turnovers = 13.5
            stats.off_rebounds = 28.0
            stats.def_rebounds = 70.0
            return stats
        except Exception as e:
            print(f"Error obteniendo stats de balldontlie: {e}")
            return None

    def get_game_result(self, game_id: str) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/games/{game_id}"
            headers = self._get_headers()
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 404:
                return {}
            response.raise_for_status()
            data = response.json()
            return {
                "home_score": data.get("home_team_score"),
                "away_score": data.get("visitor_team_score"),
                "winner": data.get("home_team", {}).get("full_name") if data.get("home_team_score", 0) > data.get("visitor_team_score", 0) else data.get("visitor_team", {}).get("full_name")
            }
        except Exception as e:
            print(f"Error obteniendo resultado de balldontlie: {e}")
            return {}


class TheSportsDBProvider(BaseDataProvider):
    def __init__(self):
        super().__init__("TheSportsDB")
        self.base_url = "https://www.thesportsdb.com/api/v1/json/3"
        self.leagues = {
            "soccer": ["4328", "4331", "4332", "4334", "4335"],
            "basketball": ["4387", "4388"],
            "baseball": ["4424"],
            "hockey": ["4380"]
        }
        self._games_cache = {}

    def get_games_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        games = []
        date_str = target_date.strftime("%Y-%m-%d")
        for sport, league_ids in self.leagues.items():
            for league_id in league_ids:
                try:
                    url = f"{self.base_url}/eventsday.php?d={date_str}&id={league_id}"
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        events = data.get("events", [])
                        for event in events:
                            game = {
                                "id": event.get("idEvent"),
                                "home_team": event.get("strHomeTeam"),
                                "away_team": event.get("strAwayTeam"),
                                "status": "finished" if event.get("intHomeScore") is not None else "scheduled",
                                "sport": sport,
                                "source": self.name,
                                "home_score": event.get("intHomeScore"),
                                "away_score": event.get("intAwayScore")
                            }
                            games.append(game)
                except Exception as e:
                    print(f"Error en TheSportsDB para liga {league_id}: {e}")
                    continue
        if games:
            self.mark_success()
        else:
            self.mark_failure()
        self._games_cache[target_date] = games
        return games

    def get_team_recent_record(self, team_name: str, end_date: date, sport: str = "soccer") -> Dict[str, int]:
        return {'wins': 0, 'losses': 0}

    def get_team_stats(self, team_name: str, target_date: date, sport: str = "soccer") -> Optional['TeamStats']:
        return None


class NBADataDotComProvider(BaseDataProvider):
    def __init__(self):
        super().__init__("NBA_Data")
        self.base_url = "https://data.nba.com/data/10s/v2015/json/mobile_teams/nba"
        self._games_cache = {}

    def get_games_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        try:
            season = target_date.year if target_date.month >= 10 else target_date.year - 1
            date_str = target_date.strftime("%Y%m%d")
            url = f"{self.base_url}/{season}/scoreboard_{date_str}.json"
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return []
            data = response.json()
            games = []
            games_list = data.get("games", []) or data.get("scoreboard", {}).get("games", [])
            for game in games_list:
                try:
                    home_team = game.get("hTeam", {}).get("triCode") or game.get("homeTeam", {}).get("teamName")
                    away_team = game.get("vTeam", {}).get("triCode") or game.get("awayTeam", {}).get("teamName")
                    game_info = {
                        "id": game.get("gameId"),
                        "home_team": home_team,
                        "away_team": away_team,
                        "status": "finished" if game.get("gameStatus") == 3 else "scheduled",
                        "sport": "basketball",
                        "source": self.name,
                        "home_score": game.get("hTeam", {}).get("score"),
                        "away_score": game.get("vTeam", {}).get("score")
                    }
                    games.append(game_info)
                except (KeyError, IndexError):
                    continue
            if games:
                self.mark_success()
            else:
                self.mark_failure()
            self._games_cache[target_date] = games
            return games
        except Exception as e:
            print(f"Error en NBADataDotComProvider: {e}")
            self.mark_failure()
            return []

    def get_team_recent_record(self, team_name: str, end_date: date, sport: str = "basketball") -> Dict[str, int]:
        return {'wins': 0, 'losses': 0}

    def get_team_stats(self, team_name: str, target_date: date, sport: str = "basketball") -> Optional['TeamStats']:
        return None


class NHLStatsAPIProvider(BaseDataProvider):
    def __init__(self):
        super().__init__("NHL_Stats")
        self.base_url = "https://statsapi.web.nhl.com/api/v1"
        self._games_cache = {}

    def get_games_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        try:
            date_str = target_date.strftime("%Y-%m-%d")
            url = f"{self.base_url}/schedule"
            params = {"date": date_str}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            games = []
            for date_info in data.get("dates", []):
                for game in date_info.get("games", []):
                    home_team = game.get("teams", {}).get("home", {}).get("team", {}).get("name")
                    away_team = game.get("teams", {}).get("away", {}).get("team", {}).get("name")
                    game_info = {
                        "id": game.get("gamePk"),
                        "home_team": home_team,
                        "away_team": away_team,
                        "status": game.get("status", {}).get("detailedState"),
                        "sport": "nhl",
                        "source": self.name,
                        "home_score": game.get("teams", {}).get("home", {}).get("score"),
                        "away_score": game.get("teams", {}).get("away", {}).get("score")
                    }
                    games.append(game_info)
            if games:
                self.mark_success()
            else:
                self.mark_failure()
            self._games_cache[target_date] = games
            return games
        except Exception as e:
            print(f"Error en NHLStatsAPIProvider: {e}")
            self.mark_failure()
            return []

    def get_team_recent_record(self, team_name: str, end_date: date, sport: str = "nhl") -> Dict[str, int]:
        return {'wins': 0, 'losses': 0}

    def get_team_stats(self, team_name: str, target_date: date, sport: str = "nhl") -> Optional['TeamStats']:
        return None


class BBCSportProvider(BaseDataProvider):
    def __init__(self):
        super().__init__("BBC_Sport")
        self.base_url = "https://www.bbc.com/sport/football/scores-fixtures"
        self._driver = None
        self._games_cache = {}

    def _get_driver(self):
        if self._driver is None:
            chrome_options = Options()
            if BBC_HEADLESS:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            service = Service(ChromeDriverManager().install())
            self._driver = webdriver.Chrome(service=service, options=chrome_options)
        return self._driver

    def _close_driver(self):
        if self._driver:
            self._driver.quit()
            self._driver = None

    def get_games_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        if not ENABLE_BBC_SPORT:
            return []
        try:
            driver = self._get_driver()
            today = date.today()
            if target_date != today:
                # Para simplificar, solo manejamos fecha actual
                return []
            driver.get(self.base_url)
            wait = WebDriverWait(driver, BBC_TIMEOUT)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".sp-c-fixture")))
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            games = []
            fixtures = soup.find_all('div', class_='sp-c-fixture')
            for fixture in fixtures:
                try:
                    home_span = fixture.find('span', class_='sp-c-fixture__team-name--home')
                    away_span = fixture.find('span', class_='sp-c-fixture__team-name--away')
                    if not home_span or not away_span:
                        continue
                    home_team = home_span.get_text(strip=True)
                    away_team = away_span.get_text(strip=True)
                    score_span = fixture.find('span', class_='sp-c-fixture__score')
                    status = "scheduled"
                    home_score = None
                    away_score = None
                    if score_span:
                        score_text = score_span.get_text(strip=True)
                        if '-' in score_text:
                            parts = score_text.split('-')
                            if len(parts) == 2:
                                home_score = int(parts[0])
                                away_score = int(parts[1])
                                status = "finished"
                    game = {
                        "id": f"bbc_{home_team}_{away_team}_{target_date.isoformat()}",
                        "home_team": home_team,
                        "away_team": away_team,
                        "status": status,
                        "sport": "soccer",
                        "source": self.name,
                        "home_score": home_score,
                        "away_score": away_score
                    }
                    games.append(game)
                except Exception as e:
                    print(f"Error procesando fixture BBC: {e}")
                    continue
            if games:
                self.mark_success()
            else:
                self.mark_failure()
            self._games_cache[target_date] = games
            return games
        except Exception as e:
            print(f"Error en BBCSportProvider: {e}")
            self.mark_failure()
            return []

    def __del__(self):
        self._close_driver()


class DataProviderManager:
    def __init__(self):
        self.providers = [
            SportsSkillsProvider(),
            ESPNProvider(),
            NBADataDotComProvider(),
            NHLStatsAPIProvider(),
            BallDontLieProvider(),
            TheSportsDBProvider(),
            OpenLigaDBProvider(),
            DraftKingsProvider(),
            BBCSportProvider()
        ]
        self.last_successful_provider = None
        self.cache = {}

    def get_games_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        cache_key = f"games_{target_date.isoformat()}"
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if datetime.now().timestamp() - cached_data["timestamp"] < 3600:
                return cached_data["data"]
        providers_to_try = []
        if self.last_successful_provider:
            providers_to_try.append(self.last_successful_provider)
            providers_to_try.extend([p for p in self.providers if p != self.last_successful_provider])
        else:
            providers_to_try = self.providers.copy()
        for provider in providers_to_try:
            if not provider.enabled:
                continue
            print(f"Intentando obtener datos desde {provider.name}...")
            games = provider.get_games_by_date(target_date)
            if games:
                print(f"✓ Datos obtenidos exitosamente desde {provider.name} ({len(games)} juegos)")
                self.last_successful_provider = provider
                self.cache[cache_key] = {"data": games, "timestamp": datetime.now().timestamp()}
                return games
            else:
                print(f"✗ {provider.name} no devolvió datos para esta fecha")
        print("⚠️ Ningún proveedor pudo obtener datos para la fecha solicitada")
        return []

    def get_soccer_games_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        """
        Obtiene partidos de fútbol usando proveedores especializados.
        Prioriza TheSportsDB, OpenLigaDB, BBC.
        """
        cache_key = f"soccer_games_{target_date.isoformat()}"
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if datetime.now().timestamp() - cached_data["timestamp"] < 3600:
                return cached_data["data"]

        soccer_providers = [
            TheSportsDBProvider(),
            OpenLigaDBProvider(),
            BBCSportProvider()
        ]
        for provider in soccer_providers:
            print(f"Intentando obtener datos de fútbol desde {provider.name}...")
            games = provider.get_games_by_date(target_date)
            if games:
                print(f"✓ Datos de fútbol obtenidos desde {provider.name} ({len(games)} juegos)")
                self.cache[cache_key] = {"data": games, "timestamp": datetime.now().timestamp()}
                return games
            else:
                print(f"✗ {provider.name} no devolvió datos de fútbol para esta fecha")
        print("⚠️ Ningún proveedor de fútbol pudo obtener datos para la fecha solicitada")
        return []

    def get_team_recent_record(self, team_name: str, end_date: date, sport: str = "mlb") -> Dict[str, int]:
        if self.last_successful_provider:
            record = self.last_successful_provider.get_team_recent_record(team_name, end_date, sport)
            if record['wins'] + record['losses'] > 0:
                return record
        for provider in self.providers:
            if provider == self.last_successful_provider:
                continue
            record = provider.get_team_recent_record(team_name, end_date, sport)
            if record['wins'] + record['losses'] > 0:
                return record
        return {'wins': 0, 'losses': 0}

    def get_team_stats(self, team_name: str, target_date: date, sport: str = "mlb") -> Optional['TeamStats']:
        if self.last_successful_provider:
            stats = self.last_successful_provider.get_team_stats(team_name, target_date, sport)
            if stats:
                return stats
        for provider in self.providers:
            if provider == self.last_successful_provider:
                continue
            stats = provider.get_team_stats(team_name, target_date, sport)
            if stats:
                return stats
        return None

    def get_game_result(self, game_id: str, provider_name: str = None) -> Dict[str, Any]:
        if provider_name:
            for provider in self.providers:
                if provider.name == provider_name:
                    return provider.get_game_result(game_id)
        for provider in self.providers:
            try:
                result = provider.get_game_result(game_id)
                if result:
                    return result
            except Exception:
                continue
        return {}

    def clear_cache(self):
        self.cache.clear()