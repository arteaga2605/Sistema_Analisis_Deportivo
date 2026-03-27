# auditor.py
"""
Módulo para el Auditor de Resultados.
Analiza predicciones vs resultados reales y genera informes de rendimiento.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
import os

# Intentar importar matplotlib para gráficos (opcional)
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️ Matplotlib no instalado. Para gráficos: pip install matplotlib")


class AuditorResultados:
    """
    Genera informes de rendimiento basados en el historial de predicciones.
    """

    def __init__(self, estado):
        self.estado = estado
        self.predicciones = estado.predicciones

    def obtener_predicciones_finalizadas(self) -> List:
        """Retorna solo predicciones con resultado real (acerto no None)."""
        return [p for p in self.predicciones if p.acerto is not None]

    def calcular_estadisticas(self) -> Dict:
        """
        Calcula estadísticas globales y por analista/deporte.
        Retorna un diccionario con:
        - total_predictions, correct, incorrect, accuracy
        - by_analyst: {analista: {predictions, correct, accuracy}}
        - by_sport: {deporte: {...}}
        - total_invested, total_profit, roi
        - profit_over_time: lista de (fecha, profit_acumulado)
        """
        predicciones = self.obtener_predicciones_finalizadas()
        total = len(predicciones)
        correct = sum(1 for p in predicciones if p.acerto)
        incorrect = total - correct
        accuracy = correct / total if total > 0 else 0

        # Por analista
        by_analyst = {}
        for p in predicciones:
            analista = p.analista or "desconocido"
            if analista not in by_analyst:
                by_analyst[analista] = {'predictions': 0, 'correct': 0, 'invested': 0, 'profit': 0}
            by_analyst[analista]['predictions'] += 1
            if p.acerto:
                by_analyst[analista]['correct'] += 1
            by_analyst[analista]['invested'] += p.monto_invertido
            profit = p.monto_invertido if p.acerto else -p.monto_invertido
            by_analyst[analista]['profit'] += profit

        for analista in by_analyst:
            preds = by_analyst[analista]['predictions']
            by_analyst[analista]['accuracy'] = by_analyst[analista]['correct'] / preds if preds > 0 else 0
            invested = by_analyst[analista]['invested']
            by_analyst[analista]['roi'] = (by_analyst[analista]['profit'] / invested) if invested > 0 else 0

        # Por deporte
        by_sport = {}
        for p in predicciones:
            deporte = p.deporte or "desconocido"
            if deporte not in by_sport:
                by_sport[deporte] = {'predictions': 0, 'correct': 0}
            by_sport[deporte]['predictions'] += 1
            if p.acerto:
                by_sport[deporte]['correct'] += 1
        for deporte in by_sport:
            preds = by_sport[deporte]['predictions']
            by_sport[deporte]['accuracy'] = by_sport[deporte]['correct'] / preds if preds > 0 else 0

        # ROI global
        total_invested = sum(p.monto_invertido for p in predicciones)
        total_profit = sum(p.monto_invertido if p.acerto else -p.monto_invertido for p in predicciones)
        roi = total_profit / total_invested if total_invested > 0 else 0

        # Evolución del beneficio acumulado
        profit_over_time = []
        # Ordenar por fecha
        sorted_preds = sorted(predicciones, key=lambda p: p.fecha)
        acum = 0
        for p in sorted_preds:
            profit = p.monto_invertido if p.acerto else -p.monto_invertido
            acum += profit
            profit_over_time.append((p.fecha, acum))

        return {
            'total_predictions': total,
            'correct': correct,
            'incorrect': incorrect,
            'accuracy': accuracy,
            'by_analyst': by_analyst,
            'by_sport': by_sport,
            'total_invested': total_invested,
            'total_profit': total_profit,
            'roi': roi,
            'profit_over_time': profit_over_time
        }

    def generar_reporte_texto(self, stats: Dict) -> str:
        """Genera un reporte de texto legible con las estadísticas."""
        lines = []
        lines.append("\n" + "="*70)
        lines.append("📊 INFORME DE RENDIMIENTO - AUDITOR DE RESULTADOS")
        lines.append("="*70)
        lines.append(f"\n📈 ESTADÍSTICAS GLOBALES:")
        lines.append(f"   Total predicciones finalizadas: {stats['total_predictions']}")
        lines.append(f"   Aciertos: {stats['correct']}")
        lines.append(f"   Fallos: {stats['incorrect']}")
        lines.append(f"   Precisión: {stats['accuracy']*100:.2f}%")
        lines.append(f"\n💰 FINANZAS:")
        lines.append(f"   Total invertido: {stats['total_invested']:.2f}")
        lines.append(f"   Ganancia/Pérdida neta: {stats['total_profit']:.2f}")
        lines.append(f"   ROI: {stats['roi']*100:.2f}%")

        lines.append("\n👥 RENDIMIENTO POR ANALISTA:")
        lines.append(f"{'Analista':<20} {'Predicciones':>12} {'Aciertos':>10} {'Precisión':>12} {'ROI':>10}")
        lines.append("-" * 70)
        for analista, data in stats['by_analyst'].items():
            lines.append(f"{analista:<20} {data['predictions']:>12} {data['correct']:>10} {data['accuracy']*100:>11.2f}% {data['roi']*100:>9.2f}%")

        lines.append("\n🏆 RENDIMIENTO POR DEPORTE:")
        lines.append(f"{'Deporte':<20} {'Predicciones':>12} {'Aciertos':>10} {'Precisión':>12}")
        lines.append("-" * 55)
        for deporte, data in stats['by_sport'].items():
            lines.append(f"{deporte:<20} {data['predictions']:>12} {data['correct']:>10} {data['accuracy']*100:>11.2f}%")

        lines.append("\n📅 EVOLUCIÓN DEL BENEFICIO ACUMULADO:")
        if stats['profit_over_time']:
            for fecha, profit in stats['profit_over_time'][-10:]:
                lines.append(f"   {fecha}: {profit:.2f}")
        else:
            lines.append("   Sin datos suficientes.")

        lines.append("\n" + "="*70)
        return "\n".join(lines)

    def generar_grafico_rendimiento(self, stats: Dict, output_file: str = None):
        """
        Genera gráficos de barras de precisión por analista y evolución del beneficio.
        Si output_file es None, muestra en pantalla; si se especifica, guarda como imagen.
        """
        if not MATPLOTLIB_AVAILABLE:
            print("⚠️ Matplotlib no instalado. No se pueden generar gráficos.")
            return

        # Gráfico 1: Precisión por analista
        analistas = list(stats['by_analyst'].keys())
        accuracy = [stats['by_analyst'][a]['accuracy']*100 for a in analistas]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        ax1.bar(analistas, accuracy, color='skyblue')
        ax1.set_ylabel('Precisión (%)')
        ax1.set_title('Precisión por Analista')
        ax1.set_ylim(0, 100)
        for i, v in enumerate(accuracy):
            ax1.text(i, v + 1, f"{v:.1f}%", ha='center')

        # Gráfico 2: Evolución del beneficio acumulado
        if stats['profit_over_time']:
            fechas = [p[0] for p in stats['profit_over_time']]
            profits = [p[1] for p in stats['profit_over_time']]
            ax2.plot(fechas, profits, marker='o', linestyle='-', color='green')
            ax2.set_xlabel('Fecha')
            ax2.set_ylabel('Beneficio Acumulado')
            ax2.set_title('Evolución del Beneficio')
            ax2.grid(True)
            # Formatear fechas
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        else:
            ax2.text(0.5, 0.5, 'Sin datos suficientes', ha='center', va='center')
            ax2.set_title('Evolución del Beneficio')

        plt.tight_layout()
        if output_file:
            plt.savefig(output_file)
            print(f"✅ Gráfico guardado en {output_file}")
        else:
            plt.show()

    def generar_reporte_completo(self, guardar_grafico: bool = True):
        """
        Genera y muestra el reporte completo, y opcionalmente guarda gráfico.
        """
        stats = self.calcular_estadisticas()
        print(self.generar_reporte_texto(stats))
        if guardar_grafico and stats['total_predictions'] > 0:
            self.generar_grafico_rendimiento(stats, output_file="reporte_rendimiento.png")