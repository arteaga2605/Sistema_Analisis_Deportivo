# apis/mlb_api.py
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from config import MLB_BASE_URL, MLB_SPORT_ID, DIAS_HISTORICO_RECIENTE


def get_schedule_by_date(date_str: str) -> List[Dict[str, Any]]:
    """
    Obtiene la programación de juegos para una fecha específica.
    date_str: formato 'YYYY-MM-DD'
    Retorna una lista de juegos (cada juego es un dict con información básica).
    """
    url = f"{MLB_BASE_URL}/schedule"
    params = {
        'sportId': MLB_SPORT_ID,
        'date': date_str
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    games = []
    # La respuesta tiene estructura: data['dates'][0]['games']
    if data.get('dates'):
        for game in data['dates'][0].get('games', []):
            games.append(game)
    return games


def get_team_info(team_id: int) -> Dict[str, Any]:
    """Obtiene información básica de un equipo por su ID."""
    url = f"{MLB_BASE_URL}/teams/{team_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json().get('teams', [{}])[0]


def get_team_recent_record(team_id: int, end_date: datetime) -> Dict[str, int]:
    """
    Calcula el récord (victorias/derrotas) de un equipo en los últimos N días.
    Si la API responde con 404 (sin datos), devuelve 0-0.
    """
    start_date = end_date - timedelta(days=DIAS_HISTORICO_RECIENTE)
    url = f"{MLB_BASE_URL}/teams/{team_id}/games"
    params = {
        'season': end_date.year,
        'startDate': start_date.strftime('%Y-%m-%d'),
        'endDate': end_date.strftime('%Y-%m-%d')
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # No hay juegos para este equipo en el período (fuera de temporada)
            return {'wins': 0, 'losses': 0}
        else:
            raise

    games = data.get('dates', [])
    wins = 0
    losses = 0
    for day in games:
        for game in day.get('games', []):
            # Determinar si el equipo fue local o visitante y si ganó
            if game.get('status', {}).get('codedGameState') != 'F':
                continue  # Juego no finalizado
            teams = game.get('teams', {})
            home_team = teams.get('home', {}).get('team', {}).get('id')
            away_team = teams.get('away', {}).get('team', {}).get('id')
            if team_id not in (home_team, away_team):
                continue
            is_home = (team_id == home_team)
            score = teams.get('home' if is_home else 'away', {}).get('score', 0)
            opponent_score = teams.get('away' if is_home else 'home', {}).get('score', 0)
            if score > opponent_score:
                wins += 1
            else:
                losses += 1
    return {'wins': wins, 'losses': losses}


def get_game_details(game_pk: int) -> Dict[str, Any]:
    """Obtiene detalles de un juego específico por su game_pk."""
    url = f"{MLB_BASE_URL}/game/{game_pk}/boxscore"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()