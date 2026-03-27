# models/estado.py (modificado)
import json
from datetime import date, datetime
from typing import List, Optional, Dict
from config import ARCHIVO_ESTADO, CAPITAL_INICIAL
from models.prediccion import Prediccion
from models.ticket import Ticket

class Estado:
    """
    Maneja el estado persistente de la empresa: capital, historial de predicciones y tickets.
    """
    def __init__(self):
        self.capital = CAPITAL_INICIAL
        self.predicciones: List[Prediccion] = []
        self.tickets: List[Ticket] = []
        self._cargar()

    def _cargar(self):
        try:
            with open(ARCHIVO_ESTADO, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.capital = data.get('capital', CAPITAL_INICIAL)
                preds = data.get('predicciones', [])
                self.predicciones = [Prediccion.from_dict(p) for p in preds]
                tickets_data = data.get('tickets', [])
                self.tickets = []
                for t_data in tickets_data:
                    # Reconstruir predicciones del ticket (ya están en el dict)
                    preds_ticket = [Prediccion.from_dict(p) for p in t_data.get('predicciones', [])]
                    ticket = Ticket(
                        id_ticket=t_data['id_ticket'],
                        fecha_creacion=date.fromisoformat(t_data['fecha_creacion']),
                        predicciones=preds_ticket,
                        monto_total=t_data['monto_total'],
                        odds=t_data.get('odds')
                    )
                    ticket.estado = t_data.get('estado', 'pendiente')
                    ticket.ganancia_neta = t_data.get('ganancia_neta', 0.0)
                    self.tickets.append(ticket)
        except (FileNotFoundError, json.JSONDecodeError):
            self.guardar()

    def guardar(self):
        data = {
            'capital': self.capital,
            'predicciones': [p.to_dict() for p in self.predicciones],
            'tickets': [t.to_dict() for t in self.tickets]
        }
        with open(ARCHIVO_ESTADO, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def agregar_prediccion(self, prediccion: Prediccion):
        self.predicciones.append(prediccion)
        self.guardar()

    def agregar_ticket(self, ticket: Ticket):
        self.tickets.append(ticket)
        self.guardar()

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

    def obtener_predicciones_por_fecha(self, fecha: date) -> List[Prediccion]:
        return [p for p in self.predicciones if p.fecha == fecha]