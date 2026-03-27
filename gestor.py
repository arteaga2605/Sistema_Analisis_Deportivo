# gestor.py
from typing import List

from models import Estado, Prediccion
from config import (
    PORCENTAJE_INVERSION_NORMAL,
    PORCENTAJE_INVERSION_RACHA,
    LIMITE_RACHA_FALLOS
)


class GestorRiesgo:
    """
    Administra el capital de la empresa, decide cuánto invertir por día
    y toma medidas en caso de rachas negativas.
    """

    def __init__(self, estado: Estado):
        self.estado = estado

    def evaluar_y_decir_inversion(self, predicciones: List[Prediccion]) -> List[float]:
        """
        Recibe una lista de predicciones y determina cuánto invertir en total,
        repartiendo equitativamente entre todas.
        Retorna una lista de montos (mismo orden que predicciones).
        """
        racha = self.estado.contar_racha_fallos()
        if racha >= LIMITE_RACHA_FALLOS:
            print(f"⚠️ ALERTA: Rachas de {racha} fallos consecutivos. Se reduce la inversión al {PORCENTAJE_INVERSION_RACHA*100:.0f}% del capital total a repartir entre las {len(predicciones)} predicciones.")
            porcentaje_total = PORCENTAJE_INVERSION_RACHA
            self._notificar_medida(racha)
        else:
            porcentaje_total = PORCENTAJE_INVERSION_NORMAL
            print(f"✅ Inversión normal: {porcentaje_total*100:.0f}% del capital total a repartir entre {len(predicciones)} predicciones.")
        
        monto_total = self.estado.capital * porcentaje_total
        monto_por_prediccion = monto_total / len(predicciones) if predicciones else 0
        montos = [monto_por_prediccion for _ in predicciones]
        for pred, monto in zip(predicciones, montos):
            pred.monto_invertido = monto
        return montos

    def _notificar_medida(self, racha: int):
        """Mensaje de asesoramiento cuando la racha de fallos supera el límite."""
        print("\n" + "="*50)
        print("CONSEJO DEL GESTOR DE RIESGO:")
        print(f"Se han detectado {racha} fallos consecutivos en las predicciones.")
        print("Se recomienda:")
        print("- Reducir drásticamente el monto invertido por día (ya aplicado).")
        print("- Revisar el modelo de predicción del analista.")
        print("- Considerar pausar las inversiones hasta que la racha se rompa.")
        print("="*50 + "\n")