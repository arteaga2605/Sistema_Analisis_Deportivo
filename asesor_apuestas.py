# asesor_apuestas.py
"""
Asesor de Apuestas Combinadas.
Evalúa la probabilidad real de un ticket seleccionado manualmente
y sugiere automáticamente el ticket de 3 juegos más probable del día.
"""

from datetime import date
from typing import List, Dict, Any, Tuple, Optional
from models import Estado

class AsesorApuestas:
    """
    Asesor que ayuda a decidir si un ticket combinado es rentable
    y sugiere el mejor ticket de 3 juegos del día.
    """

    def __init__(self):
        self.nombre = "Asesor de Apuestas"

    def _obtener_predicciones_dia(self, fecha: date) -> List:
        """Obtiene todas las predicciones del día desde el estado."""
        estado = Estado()
        # Solo predicciones del día que aún no han sido actualizadas (acerto None)
        return [p for p in estado.predicciones if p.fecha == fecha and p.acerto is None]

    def _calcular_probabilidad_combinada(self, predicciones: List) -> float:
        """Calcula la probabilidad combinada del ticket asumiendo independencia."""
        prob = 1.0
        for pred in predicciones:
            prob *= pred.probabilidad
        return prob

    def _calcular_probabilidad_ajustada(self, predicciones: List) -> float:
        """
        Calcula la probabilidad ajustada por correlación entre partidos.
        En deportes, los eventos no son completamente independientes.
        Se aplica un factor de penalización por número de partidos.
        """
        prob_independiente = self._calcular_probabilidad_combinada(predicciones)
        n = len(predicciones)
        # Factor 0.95 por cada partido extra (menor independencia)
        factor = 0.95 ** (n - 1) if n > 1 else 1.0
        return prob_independiente * factor

    def evaluar_seleccion(self, indices: List[int], fecha: date) -> Dict[str, Any]:
        """
        Evalúa la probabilidad real de un ticket formado por las predicciones
        cuyos índices se proporcionan (basado en la lista de predicciones del día).
        Retorna un diccionario con el análisis.
        """
        predicciones_dia = self._obtener_predicciones_dia(fecha)
        if not predicciones_dia:
            return {"error": "No hay predicciones para hoy."}
        
        seleccionados = []
        for idx in indices:
            if 1 <= idx <= len(predicciones_dia):
                seleccionados.append(predicciones_dia[idx-1])
            else:
                return {"error": f"Índice {idx} inválido."}
        
        if not seleccionados:
            return {"error": "No se seleccionó ninguna predicción válida."}
        
        prob_combinada = self._calcular_probabilidad_combinada(seleccionados)
        prob_ajustada = self._calcular_probabilidad_ajustada(seleccionados)
        
        detalles = []
        for pred in seleccionados:
            detalles.append({
                "partido": f"{pred.equipo_local} vs {pred.equipo_visitante}",
                "prediccion": pred.ganador_predicho,
                "probabilidad": pred.probabilidad,
                "deporte": pred.deporte
            })
        
        return {
            "seleccionados": seleccionados,
            "detalles": detalles,
            "probabilidad_combinada": prob_combinada,
            "probabilidad_ajustada": prob_ajustada,
            "num_partidos": len(seleccionados)
        }

    def sugerir_ticket_optimo(self, fecha: date, num_juegos: int = 3) -> Dict[str, Any]:
        """
        Sugiere el ticket de 'num_juegos' partidos con mayor probabilidad combinada.
        Retorna el ticket sugerido y su análisis.
        """
        predicciones_dia = self._obtener_predicciones_dia(fecha)
        if len(predicciones_dia) < num_juegos:
            return {"error": f"No hay suficientes predicciones para sugerir un ticket de {num_juegos} juegos."}
        
        from itertools import combinations
        mejor_ticket = None
        mejor_prob = 0.0
        
        for combo in combinations(predicciones_dia, num_juegos):
            prob = self._calcular_probabilidad_combinada(list(combo))
            if prob > mejor_prob:
                mejor_prob = prob
                mejor_ticket = combo
        
        if mejor_ticket:
            prob_ajustada = self._calcular_probabilidad_ajustada(list(mejor_ticket))
            detalles = []
            for pred in mejor_ticket:
                detalles.append({
                    "partido": f"{pred.equipo_local} vs {pred.equipo_visitante}",
                    "prediccion": pred.ganador_predicho,
                    "probabilidad": pred.probabilidad,
                    "deporte": pred.deporte
                })
            return {
                "ticket_sugerido": list(mejor_ticket),
                "detalles": detalles,
                "probabilidad_combinada": mejor_prob,
                "probabilidad_ajustada": prob_ajustada,
                "num_juegos": num_juegos
            }
        else:
            return {"error": "No se pudo generar una sugerencia."}

    def mostrar_evaluacion(self, evaluacion: Dict[str, Any]):
        """Imprime de forma amigable la evaluación de un ticket."""
        if "error" in evaluacion:
            print(f"\n❌ Error: {evaluacion['error']}")
            return
        
        print("\n" + "="*80)
        print("🎯 EVALUACIÓN DEL TICKET SELECCIONADO")
        print("="*80)
        for i, det in enumerate(evaluacion["detalles"], 1):
            print(f"{i}. {det['partido']}")
            print(f"   Predicción: {det['prediccion']} ({det['deporte']})")
            print(f"   Probabilidad individual: {det['probabilidad']*100:.1f}%")
        
        print("-"*40)
        print(f"📊 Probabilidad combinada (independiente): {evaluacion['probabilidad_combinada']*100:.2f}%")
        print(f"📊 Probabilidad ajustada (realista): {evaluacion['probabilidad_ajustada']*100:.2f}%")
        
        if evaluacion['probabilidad_ajustada'] > 0.40:
            print("✅ RECOMENDACIÓN: Tiene buena probabilidad de acierto. Considera invertir.")
        elif evaluacion['probabilidad_ajustada'] > 0.25:
            print("⚠️ RECOMENDACIÓN: Probabilidad media. Solo invertir si la cuota es alta.")
        else:
            print("❌ RECOMENDACIÓN: Baja probabilidad de acierto. Mejor no arriesgar.")
        print("="*80)

    def mostrar_sugerencia(self, sugerencia: Dict[str, Any]):
        """Imprime de forma amigable la sugerencia de ticket óptimo."""
        if "error" in sugerencia:
            print(f"\n❌ Error: {sugerencia['error']}")
            return
        
        print("\n" + "="*80)
        print(f"🏆 TICKET SUGERIDO ({sugerencia['num_juegos']} JUEGOS) - MAYOR PROBABILIDAD")
        print("="*80)
        for i, det in enumerate(sugerencia["detalles"], 1):
            print(f"{i}. {det['partido']}")
            print(f"   Predicción: {det['prediccion']} ({det['deporte']})")
            print(f"   Probabilidad individual: {det['probabilidad']*100:.1f}%")
        
        print("-"*40)
        print(f"📊 Probabilidad combinada: {sugerencia['probabilidad_combinada']*100:.2f}%")
        print(f"📊 Probabilidad ajustada: {sugerencia['probabilidad_ajustada']*100:.2f}%")
        print("="*80)