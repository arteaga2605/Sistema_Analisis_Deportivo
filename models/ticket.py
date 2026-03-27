# models/ticket.py
from datetime import date
from typing import List, Dict, Any, Optional
from models.prediccion import Prediccion

class Ticket:
    """
    Representa un ticket de apuesta que contiene varias predicciones.
    El ticket se considera ganador solo si TODAS las predicciones aciertan.
    """
    def __init__(self,
                 id_ticket: str,
                 fecha_creacion: date,
                 predicciones: List[Prediccion],
                 monto_total: float,
                 odds: float = None):
        self.id_ticket = id_ticket
        self.fecha_creacion = fecha_creacion
        self.predicciones = predicciones  # lista de objetos Prediccion (con sus datos)
        self.monto_total = monto_total
        self.odds = odds  # odds totales (multiplicación de odds individuales) o si es fijo
        self.estado = "pendiente"  # pendiente, ganado, perdido
        self.ganancia_neta = 0.0

    def to_dict(self) -> dict:
        return {
            'id_ticket': self.id_ticket,
            'fecha_creacion': self.fecha_creacion.isoformat(),
            'predicciones': [p.to_dict() for p in self.predicciones],
            'monto_total': self.monto_total,
            'odds': self.odds,
            'estado': self.estado,
            'ganancia_neta': self.ganancia_neta
        }

    @classmethod
    def from_dict(cls, data: dict, predicciones: List[Prediccion]):
        # Necesitamos reconstruir las predicciones a partir de sus dicts
        # Para eso, podemos crear una lista de Prediccion.from_dict
        preds = [Prediccion.from_dict(p) for p in data.get('predicciones', [])]
        ticket = cls(
            id_ticket=data['id_ticket'],
            fecha_creacion=date.fromisoformat(data['fecha_creacion']),
            predicciones=preds,
            monto_total=data['monto_total'],
            odds=data.get('odds')
        )
        ticket.estado = data.get('estado', 'pendiente')
        ticket.ganancia_neta = data.get('ganancia_neta', 0.0)
        return ticket