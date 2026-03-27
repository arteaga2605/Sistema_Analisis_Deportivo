# models/ticket.py
from datetime import date
from typing import List
import uuid

class Ticket:
    def __init__(self, id_ticket: str, fecha_creacion: date, predicciones: List, monto_total: float, odds: float):
        self.id_ticket = id_ticket
        self.fecha_creacion = fecha_creacion
        self.predicciones = predicciones  # lista de objetos Prediccion
        self.monto_total = monto_total
        self.odds = odds
        self.estado = "pendiente"  # pendiente, ganado, perdido
        self.ganancia_neta = None

    def to_dict(self):
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
    def from_dict(cls, data):
        from models.prediccion import Prediccion
        predicciones = [Prediccion.from_dict(p) for p in data['predicciones']]
        ticket = cls(
            id_ticket=data['id_ticket'],
            fecha_creacion=date.fromisoformat(data['fecha_creacion']),
            predicciones=predicciones,
            monto_total=data['monto_total'],
            odds=data['odds']
        )
        ticket.estado = data.get('estado', 'pendiente')
        ticket.ganancia_neta = data.get('ganancia_neta')
        return ticket