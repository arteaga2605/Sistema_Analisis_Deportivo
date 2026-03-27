# utils.py
import math
from typing import Tuple
from datetime import datetime


def calcular_probabilidad_ganador(record_local: dict, record_visitante: dict) -> Tuple[str, float]:
    """
    Calcula la probabilidad de victoria basada en el récord reciente.
    Retorna (equipo_con_mayor_probabilidad, probabilidad_de_ese_equipo).
    """
    # Total de juegos analizados para cada equipo
    total_local = record_local['wins'] + record_local['losses']
    total_visitante = record_visitante['wins'] + record_visitante['losses']

    # Si no hay datos, se asume 50%
    if total_local == 0 and total_visitante == 0:
        return "local", 0.5

    # Porcentaje de victorias
    win_pct_local = record_local['wins'] / total_local if total_local > 0 else 0.5
    win_pct_visitante = record_visitante['wins'] / total_visitante if total_visitante > 0 else 0.5

    # Fórmula simple: probabilidad de local = win_pct_local / (win_pct_local + win_pct_visitante)
    # Ajuste para evitar división por cero
    total_pct = win_pct_local + win_pct_visitante
    if total_pct == 0:
        prob_local = 0.5
    else:
        prob_local = win_pct_local / total_pct

    # Limitar entre 0.01 y 0.99
    prob_local = max(0.01, min(0.99, prob_local))
    prob_visitante = 1 - prob_local

    if prob_local > prob_visitante:
        return "local", prob_local
    else:
        return "visitante", prob_visitante