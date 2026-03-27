# gestor_banca.py
"""
Gestor de Banca Dinámico: aplica estrategias avanzadas de gestión de capital.
Utiliza el criterio de Kelly fraccionado para calcular el monto óptimo a invertir
en un ticket combinado, basándose en la probabilidad estimada y la cuota ofrecida.
"""

import math
from typing import List, Dict, Any, Optional

from config import (
    KELLY_FRACTION,        # Fracción del Kelly completo a usar (ej. 0.25 = 25%)
    MIN_BET_SIZE,          # Monto mínimo a apostar (unidades monetarias)
    MAX_BET_SIZE,          # Monto máximo a apostar (unidades monetarias)
    CAPITAL_INICIAL
)
from models import Ticket


class GestorBancaDinamico:
    """
    Asesora sobre el monto a invertir en un ticket combinado.
    """

    def __init__(self, capital_actual: float):
        self.capital = capital_actual

    def actualizar_capital(self, nuevo_capital: float):
        """Actualiza el capital disponible."""
        self.capital = nuevo_capital

    def calcular_apuesta_kelly(self, probabilidad: float, cuota: float) -> float:
        """
        Calcula el porcentaje del capital a apostar según el criterio de Kelly.
        Formula: f = (p * (b + 1) - 1) / b
        donde:
        - p = probabilidad de éxito (0..1)
        - b = cuota decimal - 1 (ganancia neta por unidad apostada)
        """
        if cuota <= 1:
            return 0.0  # cuota inválida
        b = cuota - 1
        if b <= 0:
            return 0.0
        # Kelly completo
        f = (probabilidad * (b + 1) - 1) / b
        # Limitar a rango razonable y aplicar fracción
        f = max(0.0, min(0.25, f))  # Kelly completo rara vez > 25%
        f = f * KELLY_FRACTION
        return f

    def sugerir_apuesta(self, ticket: Ticket) -> float:
        """
        Sugiere el monto a invertir para un ticket dado.
        Si el ticket tiene cuota_total, la usa. Si no, estima una cuota a partir
        de las probabilidades individuales (para apuestas combinadas).
        """
        if not ticket.juegos:
            return 0.0

        # Determinar la cuota del ticket
        if ticket.cuota_total is not None:
            cuota = ticket.cuota_total
        else:
            # Estimar cuota combinada: producto de (1 / probabilidad) de cada juego
            # Esto es una aproximación; en realidad la cuota la da la casa.
            # Si no hay cuota, usamos probabilidades para estimar una cuota justa.
            cuota_estimada = 1.0
            for juego in ticket.juegos:
                # Cada juego tiene una probabilidad de acierto
                prob = juego.probabilidad
                # Cuota justa = 1 / prob, pero con límite
                cuota_juego = 1.0 / prob if prob > 0 else 1.0
                cuota_estimada *= cuota_juego
            cuota = cuota_estimada

        # Probabilidad combinada del ticket: producto de probabilidades individuales
        prob_combinada = 1.0
        for juego in ticket.juegos:
            prob_combinada *= juego.probabilidad

        # Calcular porcentaje Kelly
        fraccion = self.calcular_apuesta_kelly(prob_combinada, cuota)

        # Monto a apostar
        monto = self.capital * fraccion

        # Aplicar límites
        monto = max(MIN_BET_SIZE, min(MAX_BET_SIZE, monto))

        # No apostar más del capital disponible
        monto = min(monto, self.capital)

        return monto

    def evaluar_ticket(self, ticket: Ticket) -> Dict[str, Any]:
        """
        Devuelve un análisis completo del ticket: monto sugerido, valor esperado, etc.
        """
        monto_sugerido = self.sugerir_apuesta(ticket)

        # Calcular valor esperado
        prob_combinada = 1.0
        for juego in ticket.juegos:
            prob_combinada *= juego.probabilidad
        cuota = ticket.cuota_total if ticket.cuota_total is not None else 1.0 / prob_combinada
        valor_esperado = (prob_combinada * cuota - 1) * 100  # en porcentaje

        return {
            "monto_sugerido": monto_sugerido,
            "probabilidad_combinada": prob_combinada,
            "cuota_utilizada": cuota,
            "valor_esperado_porcentaje": valor_esperado,
            "riesgo_relativo": "Alto" if prob_combinada < 0.3 else "Medio" if prob_combinada < 0.6 else "Bajo"
        }