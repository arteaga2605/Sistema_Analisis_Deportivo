# models/estado.py
import json
from datetime import date, datetime
from typing import List, Optional, Dict, Any

from config import ARCHIVO_ESTADO, CAPITAL_INICIAL
from models.prediccion import Prediccion
from models.ticket import Ticket


class SugerenciaTicket:
    """Registro de una sugerencia de ticket generada por el Asesor de Apuestas."""
    def __init__(self, fecha: date, sugerencia_id: str, detalles: List[Dict], probabilidad: float):
        self.fecha = fecha
        self.sugerencia_id = sugerencia_id
        self.detalles = detalles  # lista de dict con partido, prediccion, etc.
        self.probabilidad = probabilidad
        self.seguido = False  # si el usuario decidió seguir la sugerencia
        self.acerto = None    # si se siguió y acertó

    def to_dict(self) -> dict:
        return {
            'fecha': self.fecha.isoformat(),
            'sugerencia_id': self.sugerencia_id,
            'detalles': self.detalles,
            'probabilidad': self.probabilidad,
            'seguido': self.seguido,
            'acerto': self.acerto
        }

    @classmethod
    def from_dict(cls, data: dict):
        obj = cls(
            fecha=date.fromisoformat(data['fecha']),
            sugerencia_id=data['sugerencia_id'],
            detalles=data['detalles'],
            probabilidad=data['probabilidad']
        )
        obj.seguido = data.get('seguido', False)
        obj.acerto = data.get('acerto')
        return obj


class EvaluacionTicket:
    """Registro de una evaluación de ticket realizada por el Analista de Tickets."""
    def __init__(self, fecha: date, ticket_id: str, predicciones_ids: List[str], 
                 probabilidad_real: float, recomendacion: str, acerto: Optional[bool] = None):
        self.fecha = fecha
        self.ticket_id = ticket_id
        self.predicciones_ids = predicciones_ids
        self.probabilidad_real = probabilidad_real
        self.recomendacion = recomendacion  # "CONSERVAR" o "RECOMENDADO CANCELAR"
        self.acerto = acerto  # si la recomendación fue correcta (si el ticket ganó/perdió según recomendación)

    def to_dict(self) -> dict:
        return {
            'fecha': self.fecha.isoformat(),
            'ticket_id': self.ticket_id,
            'predicciones_ids': self.predicciones_ids,
            'probabilidad_real': self.probabilidad_real,
            'recomendacion': self.recomendacion,
            'acerto': self.acerto
        }

    @classmethod
    def from_dict(cls, data: dict):
        obj = cls(
            fecha=date.fromisoformat(data['fecha']),
            ticket_id=data['ticket_id'],
            predicciones_ids=data['predicciones_ids'],
            probabilidad_real=data['probabilidad_real'],
            recomendacion=data['recomendacion']
        )
        obj.acerto = data.get('acerto')
        return obj


class Estado:
    def __init__(self):
        self.capital = CAPITAL_INICIAL
        self.predicciones: List[Prediccion] = []
        self.tickets: List[Ticket] = []
        self.sugerencias: List[SugerenciaTicket] = []
        self.evaluaciones: List[EvaluacionTicket] = []
        self._cargar()

    def _cargar(self):
        try:
            with open(ARCHIVO_ESTADO, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.capital = data.get('capital', CAPITAL_INICIAL)
                preds = data.get('predicciones', [])
                self.predicciones = [Prediccion.from_dict(p) for p in preds]
                tickets = data.get('tickets', [])
                self.tickets = [Ticket.from_dict(t) for t in tickets]
                sugs = data.get('sugerencias', [])
                self.sugerencias = [SugerenciaTicket.from_dict(s) for s in sugs]
                evals = data.get('evaluaciones', [])
                self.evaluaciones = [EvaluacionTicket.from_dict(e) for e in evals]
        except (FileNotFoundError, json.JSONDecodeError):
            self.guardar()

    def guardar(self):
        data = {
            'capital': self.capital,
            'predicciones': [p.to_dict() for p in self.predicciones],
            'tickets': [t.to_dict() for t in self.tickets],
            'sugerencias': [s.to_dict() for s in self.sugerencias],
            'evaluaciones': [e.to_dict() for e in self.evaluaciones]
        }
        with open(ARCHIVO_ESTADO, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def agregar_prediccion(self, prediccion: Prediccion):
        self.predicciones.append(prediccion)
        self.guardar()

    def agregar_ticket(self, ticket: Ticket):
        self.tickets.append(ticket)
        self.guardar()

    def agregar_sugerencia(self, sugerencia: SugerenciaTicket):
        self.sugerencias.append(sugerencia)
        self.guardar()

    def agregar_evaluacion(self, evaluacion: EvaluacionTicket):
        self.evaluaciones.append(evaluacion)
        self.guardar()

    def obtener_predicciones_por_fecha(self, fecha: date) -> List[Prediccion]:
        return [p for p in self.predicciones if p.fecha == fecha and p.acerto is None]

    def obtener_ultimas_predicciones(self, n: int = None) -> List[Prediccion]:
        if n is None:
            return self.predicciones[::-1]
        return self.predicciones[-n:][::-1]

    def contar_racha_fallos(self) -> int:
        racha = 0
        for pred in reversed(self.predicciones):
            if pred.acerto is None:
                continue
            if not pred.acerto:
                racha += 1
            else:
                break
        return racha

    def obtener_estadisticas_analistas(self) -> Dict[str, Dict[str, int]]:
        stats = {}
        for pred in self.predicciones:
            if pred.acerto is None:
                continue
            analista = pred.analista or "desconocido"
            if analista not in stats:
                stats[analista] = {'aciertos': 0, 'fallos': 0}
            if pred.acerto:
                stats[analista]['aciertos'] += 1
            else:
                stats[analista]['fallos'] += 1
        return stats