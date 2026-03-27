# models/prediccion.py
from datetime import date
from typing import Optional


class Prediccion:
    """
    Representa una predicción realizada para un juego.
    """
    def __init__(self,
                 fecha: date,
                 equipo_local: str,
                 equipo_visitante: str,
                 ganador_predicho: str,
                 probabilidad: float,
                 deporte: Optional[str] = None,
                 marcador_estimado: Optional[str] = None,
                 comentario: Optional[str] = None,
                 analista: Optional[str] = None,
                 resultado_real: Optional[str] = None,
                 acerto: Optional[bool] = None,
                 monto_invertido: float = 0.0):
        self.fecha = fecha
        self.equipo_local = equipo_local
        self.equipo_visitante = equipo_visitante
        self.ganador_predicho = ganador_predicho
        self.probabilidad = probabilidad
        self.deporte = deporte
        self.marcador_estimado = marcador_estimado
        self.comentario = comentario
        self.analista = analista
        self.resultado_real = resultado_real
        self.acerto = acerto
        self.monto_invertido = monto_invertido

    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario para serialización JSON."""
        return {
            'fecha': self.fecha.isoformat(),
            'equipo_local': self.equipo_local,
            'equipo_visitante': self.equipo_visitante,
            'ganador_predicho': self.ganador_predicho,
            'probabilidad': self.probabilidad,
            'deporte': self.deporte,
            'marcador_estimado': self.marcador_estimado,
            'comentario': self.comentario,
            'analista': self.analista,
            'resultado_real': self.resultado_real,
            'acerto': self.acerto,
            'monto_invertido': self.monto_invertido
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Crea un objeto desde un diccionario (deserialización)."""
        return cls(
            fecha=date.fromisoformat(data['fecha']),
            equipo_local=data['equipo_local'],
            equipo_visitante=data['equipo_visitante'],
            ganador_predicho=data['ganador_predicho'],
            probabilidad=data['probabilidad'],
            deporte=data.get('deporte'),
            marcador_estimado=data.get('marcador_estimado'),
            comentario=data.get('comentario'),
            analista=data.get('analista'),
            resultado_real=data.get('resultado_real'),
            acerto=data.get('acerto'),
            monto_invertido=data.get('monto_invertido', 0.0)
        )