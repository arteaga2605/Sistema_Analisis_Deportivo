# main.py
import sys
import argparse
from datetime import date, datetime, timedelta
from typing import List, Optional

from models import Estado, Prediccion
from models.ticket import Ticket
from analista import AnalistaDeportivo
from analista_alternativo import AnalistaAlternativo
from analista_futbol import AnalistaFutbol
from analista_excel import AnalistaExcel          # <-- NUEVO
from gestor import GestorRiesgo
from apis import get_schedule_by_date, get_game_details
from config import USE_MULTI_PROVIDER, UMBRAL_PROBABILIDAD
from auditor import AuditorResultados
from analista_tickets import TicketAnalyst
from asesor_apuestas import AsesorApuestas
from animacion import mostrar_animacion

if USE_MULTI_PROVIDER:
    from data_providers import DataProviderManager
    data_manager = DataProviderManager()


def obtener_resultados_reales(fecha: date) -> dict:
    resultados = {}
    if USE_MULTI_PROVIDER:
        print(f"Obteniendo resultados para {fecha} usando multi-proveedor...")
        juegos = data_manager.get_games_by_date(fecha)
        for juego in juegos:
            if juego.get("status") == "scheduled":
                continue
            home_team = juego.get("home_team")
            away_team = juego.get("away_team")
            home_score = juego.get("home_score")
            away_score = juego.get("away_score")
            if home_score is not None and away_score is not None:
                ganador = home_team if home_score > away_score else away_team
                resultados[(home_team, away_team)] = (ganador, f"{home_score}-{away_score}")
        if not resultados:
            print("No se encontraron resultados con multi-proveedor, intentando con MLB API...")
            resultados = obtener_resultados_mlb_api(fecha)
    else:
        resultados = obtener_resultados_mlb_api(fecha)
    return resultados


def obtener_resultados_mlb_api(fecha: date) -> dict:
    fecha_str = fecha.isoformat()
    juegos = get_schedule_by_date(fecha_str)
    resultados = {}
    for juego in juegos:
        if juego.get('status', {}).get('codedGameState') != 'F':
            continue
        home_team = juego['teams']['home']['team']['name']
        away_team = juego['teams']['away']['team']['name']
        home_score = juego['teams']['home']['score']
        away_score = juego['teams']['away']['score']
        ganador = home_team if home_score > away_score else away_team
        resultados[(home_team, away_team)] = (ganador, f"{home_score}-{away_score}")
    return resultados


def actualizar_estado_con_resultados(estado: Estado, fecha: date):
    resultados = obtener_resultados_reales(fecha)
    for pred in estado.predicciones:
        if pred.fecha != fecha:
            continue
        key = (pred.equipo_local, pred.equipo_visitante)
        if key not in resultados:
            print(f"Advertencia: No se encontró resultado para {pred.equipo_local} vs {pred.equipo_visitante} en {fecha}")
            continue
        ganador_real, marcador = resultados[key]
        pred.resultado_real = f"{ganador_real} ({marcador})"
        acerto = (pred.ganador_predicho == ganador_real)
        pred.acerto = acerto
    for ticket in estado.tickets:
        if ticket.fecha_creacion != fecha:
            continue
        if ticket.estado != "pendiente":
            continue
        todas_acertaron = True
        for pred in ticket.predicciones:
            pred_actualizada = None
            for p in estado.predicciones:
                if p.fecha == fecha and p.equipo_local == pred.equipo_local and p.equipo_visitante == pred.equipo_visitante:
                    pred_actualizada = p
                    break
            if not pred_actualizada or pred_actualizada.acerto is None:
                todas_acertaron = False
                break
            if not pred_actualizada.acerto:
                todas_acertaron = False
                break
        if todas_acertaron:
            ticket.estado = "ganado"
            ticket.ganancia_neta = ticket.monto_total * (ticket.odds - 1)
            estado.capital += ticket.monto_total * ticket.odds
            print(f"✅ Ticket {ticket.id_ticket} ganado! Ganancia neta: +{ticket.ganancia_neta:.2f}")
        else:
            ticket.estado = "perdido"
            ticket.ganancia_neta = -ticket.monto_total
            estado.capital -= ticket.monto_total
            print(f"❌ Ticket {ticket.id_ticket} perdido. Pérdida: -{ticket.monto_total:.2f}")
    estado.guardar()
    print(f"Capital actualizado: {estado.capital:.2f}")


def ejecutar_prediccion():
    mostrar_animacion('predict')
    print("=== SISTEMA DE ANÁLISIS DEPORTIVO - FASE DE PREDICCIÓN ===")
    estado = Estado()
    analista1 = AnalistaDeportivo()
    analista2 = AnalistaAlternativo()
    gestor = GestorRiesgo(estado)

    hoy = date.today()
    predicciones1 = analista1.analizar_juegos_dia(hoy)
    predicciones2 = analista2.analizar_juegos_dia(hoy)
    todas_predicciones = predicciones1 + predicciones2

    if not todas_predicciones:
        print("No hay predicciones con suficiente probabilidad para hoy.")
        return

    montos = gestor.evaluar_y_decir_inversion(todas_predicciones)

    print("\n📊 RESUMEN DE INVERSIONES PARA HOY:")
    print("=" * 90)
    total_invertido = 0.0
    for pred, monto in zip(todas_predicciones, montos):
        total_invertido += monto
        condicion = "🏠 LOCAL" if pred.ganador_predicho == pred.equipo_local else "✈️ VISITANTE"
        marcador_txt = f" → Marcador estimado: {pred.marcador_estimado}" if pred.marcador_estimado else ""
        print(f"🎯 [{pred.analista}] {pred.deporte} | {pred.equipo_local} vs {pred.equipo_visitante}")
        print(f"   📈 Predicción: {pred.ganador_predicho} ({condicion}) con {pred.probabilidad*100:.1f}% de probabilidad{marcador_txt}")
        print(f"   💬 Comentario: {pred.comentario}")
        print(f"   💰 Inversión sugerida: {monto:.2f}")
        print("-" * 90)
    print(f"\n💰 TOTAL A INVERTIR HOY: {total_invertido:.2f}")
    print(f"💵 CAPITAL RESTANTE (después de inversiones): {estado.capital - total_invertido:.2f}")

    for pred in todas_predicciones:
        estado.agregar_prediccion(pred)

    print("\n✅ Predicciones guardadas. Ejecute '--create-ticket' para crear un ticket con las predicciones del día.")


def crear_ticket():
    mostrar_animacion('ticket')
    estado = Estado()
    hoy = date.today()
    predicciones_hoy = estado.obtener_predicciones_por_fecha(hoy)
    if not predicciones_hoy:
        print("No hay predicciones para hoy. Ejecute primero '--predict'.")
        return

    print("\n=== CREAR TICKET ===")
    print("Predicciones disponibles para hoy:")
    for idx, pred in enumerate(predicciones_hoy, 1):
        print(f"{idx}. [{pred.analista}] {pred.deporte} | {pred.equipo_local} vs {pred.equipo_visitante}")
        print(f"   Predicción: {pred.ganador_predicho} ({pred.probabilidad*100:.1f}%)")
        print(f"   Comentario: {pred.comentario}")
        print("-" * 50)

    seleccion = input("\nIngrese los números de las predicciones que desea incluir en el ticket (separados por comas, ej: 1,3,5): ")
    try:
        indices = [int(x.strip()) for x in seleccion.split(',')]
    except:
        print("Entrada inválida.")
        return
    seleccionados = []
    for i in indices:
        if 1 <= i <= len(predicciones_hoy):
            seleccionados.append(predicciones_hoy[i-1])
        else:
            print(f"Índice {i} inválido. Se omitirá.")
    if not seleccionados:
        print("No se seleccionó ninguna predicción válida.")
        return

    prob_combinada = 1.0
    for p in seleccionados:
        prob_combinada *= p.probabilidad
    print(f"\n📊 Probabilidad combinada estimada: {prob_combinada*100:.2f}%")

    try:
        odds = float(input("Ingrese las odds totales del ticket (ganancia = monto * odds si acierta): "))
        if odds <= 1:
            print("Odds deben ser mayores a 1.")
            return
    except:
        print("Odds inválidas.")
        return

    p = prob_combinada
    q = 1 - p
    b = odds - 1
    if b > 0:
        kelly = (p * b - q) / b
    else:
        kelly = 0
    kelly = max(0, min(1, kelly))
    kelly_fraccionado = kelly * 0.25

    print(f"\n💡 Sugerencia de Kelly: {kelly*100:.2f}% de tu capital actual ({estado.capital:.2f})")
    print(f"   Kelly fraccionado (25%): {kelly_fraccionado*100:.2f}% → {estado.capital * kelly_fraccionado:.2f}")

    usar_sugerencia = input("¿Deseas usar la sugerencia de Kelly? (s/n): ").strip().lower()
    if usar_sugerencia in ['s', 'si', 'y', 'yes']:
        monto_total = estado.capital * kelly_fraccionado
        print(f"Monto sugerido: {monto_total:.2f}")
    else:
        try:
            monto_total = float(input("Ingrese el monto total a apostar en este ticket: "))
            if monto_total <= 0:
                print("Monto debe ser positivo.")
                return
        except:
            print("Monto inválido.")
            return

    ticket_id = f"TICKET_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    ticket = Ticket(
        id_ticket=ticket_id,
        fecha_creacion=hoy,
        predicciones=seleccionados,
        monto_total=monto_total,
        odds=odds
    )
    estado.agregar_ticket(ticket)
    print(f"\n✅ Ticket creado con ID: {ticket_id}")
    print(f"   Apuesta: {monto_total:.2f} | Odds: {odds:.2f}")
    print("   Partidos incluidos:")
    for pred in seleccionados:
        print(f"   - {pred.equipo_local} vs {pred.equipo_visitante} -> {pred.ganador_predicho}")


def listar_tickets():
    estado = Estado()
    if not estado.tickets:
        print("No hay tickets registrados.")
        return
    print("\n=== LISTA DE TICKETS ===")
    for ticket in estado.tickets:
        print(f"ID: {ticket.id_ticket} | Fecha: {ticket.fecha_creacion} | Monto: {ticket.monto_total:.2f} | Odds: {ticket.odds:.2f} | Estado: {ticket.estado}")
        print("  Partidos:")
        for pred in ticket.predicciones:
            print(f"    {pred.equipo_local} vs {pred.equipo_visitante} -> {pred.ganador_predicho}")
        print("-" * 50)


def mostrar_comparativa():
    mostrar_animacion('compare')
    estado = Estado()
    stats = estado.obtener_estadisticas_analistas()
    print("\n=== COMPARATIVA DE ANALISTAS ===")
    print("Analista\t\tAciertos\tFallos\t% Acierto")
    print("-" * 50)
    for analista, datos in stats.items():
        total = datos['aciertos'] + datos['fallos']
        pct = (datos['aciertos'] / total * 100) if total > 0 else 0
        print(f"{analista:<20}\t{datos['aciertos']}\t\t{datos['fallos']}\t{pct:.1f}%")
    print("=" * 50)


def ejecutar_actualizacion():
    mostrar_animacion('update')
    print("=== SISTEMA DE ANÁLISIS DEPORTIVO - ACTUALIZACIÓN DE RESULTADOS ===")
    estado = Estado()
    fecha = date.today() - timedelta(days=1)
    print(f"Actualizando resultados para {fecha.isoformat()}...")
    actualizar_estado_con_resultados(estado, fecha)


def mostrar_estado():
    mostrar_animacion('status')
    estado = Estado()
    print("=== ESTADO DE LA EMPRESA ===")
    print(f"💰 Capital actual: {estado.capital:.2f}")
    print("\n📋 ÚLTIMAS 10 PREDICCIONES (más recientes primero):")
    print("=" * 80)
    ultimas = estado.obtener_ultimas_predicciones(10)
    for i, pred in enumerate(ultimas, 1):
        acerto_str = ""
        if pred.acerto is not None:
            acerto_str = "✔️ ACERTÓ" if pred.acerto else "❌ FALLÓ"
        marcador_txt = f" (estimado: {pred.marcador_estimado})" if pred.marcador_estimado else ""
        print(f"{i}. {pred.fecha} | {pred.deporte or ''} | {pred.equipo_local} vs {pred.equipo_visitante}")
        print(f"   Predicción: {pred.ganador_predicho} ({pred.probabilidad*100:.1f}%){marcador_txt}")
        print(f"   Comentario: {pred.comentario}")
        print(f"   Invertido: {pred.monto_invertido:.2f} | Resultado real: {pred.resultado_real or 'Pendiente'} {acerto_str}")
        print("-" * 80)
    print(f"\n⚠️ Racha actual de fallos: {estado.contar_racha_fallos()}")


def ejecutar_prediccion_soccer():
    mostrar_animacion('soccer')
    print("=== ANÁLISIS EXCLUSIVO DE FÚTBOL ===")
    estado = Estado()
    analista = AnalistaFutbol()
    hoy = date.today()
    predicciones = analista.analizar_juegos_dia(hoy)
    if not predicciones:
        print("No hay predicciones de fútbol con suficiente probabilidad para hoy.")
        return

    print("\n📊 PREDICCIONES DE FÚTBOL PARA HOY:")
    print("=" * 90)
    for pred in predicciones:
        condicion = "🏠 LOCAL" if pred.ganador_predicho == pred.equipo_local else "✈️ VISITANTE"
        print(f"🎯 [{pred.analista}] {pred.deporte} | {pred.equipo_local} vs {pred.equipo_visitante}")
        print(f"   📈 Predicción: {pred.ganador_predicho} ({condicion}) con {pred.probabilidad*100:.1f}%")
        print(f"   💬 Comentario: {pred.comentario}")
        print("-" * 90)

    for pred in predicciones:
        estado.agregar_prediccion(pred)
    print("\n✅ Predicciones guardadas.")


def analizar_tickets():
    """Ejecuta el analista de tickets para evaluar tickets activos."""
    mostrar_animacion('ticket_analyst')
    print("=== ANÁLISIS DE TICKETS ACTIVOS ===")
    analista = TicketAnalyst()
    analista.analizar_tickets_activos()


def evaluar_ticket():
    """Evalúa la probabilidad real de un ticket seleccionado por el usuario."""
    mostrar_animacion('evaluate')
    print("=== EVALUACIÓN DE TICKET PERSONALIZADO ===")
    
    estado = Estado()
    hoy = date.today()
    predicciones_hoy = estado.obtener_predicciones_por_fecha(hoy)
    if not predicciones_hoy:
        print("No hay predicciones para hoy. Ejecute primero '--predict'.")
        return
    
    print("\nPredicciones disponibles:")
    for idx, pred in enumerate(predicciones_hoy, 1):
        print(f"{idx}. {pred.equipo_local} vs {pred.equipo_visitante} -> {pred.ganador_predicho} ({pred.probabilidad*100:.1f}%)")
    
    seleccion = input("\nIngrese los números de las predicciones a evaluar (separados por comas, ej: 1,3,5): ")
    try:
        indices = [int(x.strip()) for x in seleccion.split(',')]
    except:
        print("Entrada inválida.")
        return
    
    asesor = AsesorApuestas()
    evaluacion = asesor.evaluar_seleccion(indices, hoy)
    asesor.mostrar_evaluacion(evaluacion)


def sugerir_ticket():
    """Sugiere el ticket de 3 juegos más probable del día."""
    mostrar_animacion('suggest')
    print("=== SUGERENCIA DE TICKET ÓPTIMO ===")
    asesor = AsesorApuestas()
    sugerencia = asesor.sugerir_ticket_optimo(date.today(), num_juegos=3)
    asesor.mostrar_sugerencia(sugerencia)


def ejecutar_analisis_excel():
    """Ejecuta el analista offline basado en Excel."""
    mostrar_animacion('excel')
    print("=== ANÁLISIS OFFLINE CON EXCEL ===")
    analista = AnalistaExcel()
    hoy = date.today()
    predicciones = analista.analizar_juegos_dia(hoy)
    if not predicciones:
        print("No hay predicciones con suficiente probabilidad para hoy.")
        return

    print("\n📊 PREDICCIONES BASADAS EN EXCEL (OFFLINE):")
    print("=" * 90)
    for pred in predicciones:
        condicion = "🏠 LOCAL" if pred.ganador_predicho == pred.equipo_local else "✈️ VISITANTE"
        print(f"🎯 [{pred.analista}] {pred.deporte} | {pred.equipo_local} vs {pred.equipo_visitante}")
        print(f"   📈 Predicción: {pred.ganador_predicho} ({condicion}) con {pred.probabilidad*100:.1f}%")
        print(f"   💬 Comentario: {pred.comentario}")
        print("-" * 90)

    # Guardar predicciones (opcional, para histórico)
    estado = Estado()
    for pred in predicciones:
        estado.agregar_prediccion(pred)
    print("\n✅ Predicciones guardadas.")


def main():
    parser = argparse.ArgumentParser(description='Sistema de análisis deportivo')
    parser.add_argument('--predict', action='store_true', help='Ejecutar fase de predicción (juegos del día)')
    parser.add_argument('--update', action='store_true', help='Actualizar resultados de los juegos de ayer')
    parser.add_argument('--status', action='store_true', help='Mostrar estado actual de la empresa')
    parser.add_argument('--compare', action='store_true', help='Comparar rendimiento de analistas')
    parser.add_argument('--create-ticket', action='store_true', help='Crear un ticket con predicciones del día')
    parser.add_argument('--list-tickets', action='store_true', help='Listar todos los tickets creados')
    parser.add_argument('--report', action='store_true', help='Generar informe de rendimiento (Auditor de Resultados)')
    parser.add_argument('--soccer', action='store_true', help='Ejecutar análisis exclusivo de fútbol (Analista Fútbol)')
    parser.add_argument('--analyze-tickets', action='store_true', help='Analizar tickets activos (probabilidad real + sentimiento social)')
    parser.add_argument('--evaluate-ticket', action='store_true', help='Evaluar probabilidad real de un ticket seleccionado manualmente')
    parser.add_argument('--suggest-ticket', action='store_true', help='Sugerir el ticket de 3 juegos más probable del día')
    parser.add_argument('--excel', action='store_true', help='Ejecutar análisis offline basado en archivo Excel')
    args = parser.parse_args()

    if args.predict:
        ejecutar_prediccion()
    elif args.update:
        ejecutar_actualizacion()
    elif args.status:
        mostrar_estado()
    elif args.compare:
        mostrar_comparativa()
    elif args.create_ticket:
        crear_ticket()
    elif args.list_tickets:
        listar_tickets()
    elif args.report:
        mostrar_animacion('report')
        estado = Estado()
        auditor = AuditorResultados(estado)
        auditor.generar_reporte_completo(guardar_grafico=True)
    elif args.soccer:
        ejecutar_prediccion_soccer()
    elif args.analyze_tickets:
        analizar_tickets()
    elif args.evaluate_ticket:
        evaluar_ticket()
    elif args.suggest_ticket:
        sugerir_ticket()
    elif args.excel:
        ejecutar_analisis_excel()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()