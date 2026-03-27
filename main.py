# main.py
import sys
import argparse
from datetime import date, datetime, timedelta
from typing import List, Optional

from models import Estado, Prediccion
from models.ticket import Ticket
from analista import AnalistaDeportivo
from analista_alternativo import AnalistaAlternativo
from gestor import GestorRiesgo
from apis import get_schedule_by_date, get_game_details
from config import USE_MULTI_PROVIDER, UMBRAL_PROBABILIDAD

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
    """
    Actualiza predicciones y tickets con resultados reales.
    """
    resultados = obtener_resultados_reales(fecha)
    # Actualizar predicciones individuales
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
        # El capital ya se ajustó con los tickets; aquí solo actualizamos predicciones
    # Actualizar tickets
    for ticket in estado.tickets:
        if ticket.fecha_creacion != fecha:
            continue
        if ticket.estado != "pendiente":
            continue
        # Verificar si todas las predicciones del ticket acertaron
        todas_acertaron = True
        for pred in ticket.predicciones:
            # Buscar la predicción actualizada en el estado
            # Nota: la predicción en el ticket puede no tener el resultado actualizado.
            # Buscamos por equipo y fecha.
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
            ticket.ganancia_neta = ticket.monto_total * (ticket.odds - 1)  # ganancia neta
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

    # Guardar predicciones
    for pred in todas_predicciones:
        estado.agregar_prediccion(pred)

    print("\n✅ Predicciones guardadas. Ejecute '--create-ticket' para crear un ticket con las predicciones del día.")


def crear_ticket():
    """
    Permite al usuario crear un ticket seleccionando predicciones del día actual,
    con recomendación basada en Kelly (Gestor de Banca Dinámico).
    """
    estado = Estado()
    hoy = date.today()
    predicciones_hoy = estado.obtener_predicciones_por_fecha(hoy)
    if not predicciones_hoy:
        print("No hay predicciones para hoy. Ejecute primero '--predict'.")
        return

    print("\n=== CREAR TICKET (con Gestor de Banca Dinámico) ===")
    print("Predicciones disponibles para hoy:")
    for idx, pred in enumerate(predicciones_hoy, 1):
        print(f"{idx}. [{pred.analista}] {pred.deporte} | {pred.equipo_local} vs {pred.equipo_visitante}")
        print(f"   Predicción: {pred.ganador_predicho} ({pred.probabilidad*100:.1f}%)")
        print(f"   Comentario: {pred.comentario}")
        print("-" * 50)

    # Seleccionar predicciones
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

    # Calcular probabilidad combinada del ticket (producto de probabilidades individuales)
    prob_combinada = 1.0
    for pred in seleccionados:
        prob_combinada *= pred.probabilidad

    print(f"\n📊 Probabilidad combinada del ticket: {prob_combinada*100:.2f}%")

    # Solicitar odds totales
    try:
        odds = float(input("Ingrese las odds totales del ticket (ganancia = monto * odds si acierta): "))
        if odds <= 1:
            print("Odds deben ser mayores a 1.")
            return
    except:
        print("Odds inválidas.")
        return

    # Calcular fracción de Kelly
    # f = p - (1-p)/(odds-1)
    if odds > 1:
        kelly_f = prob_combinada - (1 - prob_combinada) / (odds - 1)
    else:
        kelly_f = 0
    # Limitar a valores razonables
    kelly_f = max(0, min(1, kelly_f))
    
    # Factor de riesgo (Kelly fraccionado). Por defecto 25% para ser conservador.
    riesgo_factor = 0.25
    monto_sugerido = estado.capital * kelly_f * riesgo_factor

    print(f"\n💡 Recomendación Kelly: fracción óptima = {kelly_f*100:.2f}% del capital")
    print(f"   Aplicando factor de riesgo {riesgo_factor*100:.0f}%, monto sugerido: {monto_sugerido:.2f}")

    # Solicitar monto total
    monto_input = input(f"Ingrese el monto total a apostar en este ticket (Enter para usar sugerido {monto_sugerido:.2f}): ")
    if monto_input.strip() == "":
        monto_total = monto_sugerido
    else:
        try:
            monto_total = float(monto_input)
            if monto_total <= 0:
                print("Monto debe ser positivo.")
                return
        except:
            print("Monto inválido.")
            return

    # Crear ticket
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
    print(f"   Apuesta: {monto_total:.2f} | Odds: {odds:.2f} | Probabilidad combinada: {prob_combinada*100:.2f}%")
    print("   Partidos incluidos:")
    for pred in seleccionados:
        print(f"   - {pred.equipo_local} vs {pred.equipo_visitante} -> {pred.ganador_predicho}")


def listar_tickets():
    """
    Muestra todos los tickets creados.
    """
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
    print("=== SISTEMA DE ANÁLISIS DEPORTIVO - ACTUALIZACIÓN DE RESULTADOS ===")
    estado = Estado()
    fecha = date.today() - timedelta(days=1)
    print(f"Actualizando resultados para {fecha.isoformat()}...")
    actualizar_estado_con_resultados(estado, fecha)


def mostrar_estado():
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


def main():
    parser = argparse.ArgumentParser(description='Sistema de análisis deportivo')
    parser.add_argument('--predict', action='store_true', help='Ejecutar fase de predicción (juegos del día)')
    parser.add_argument('--update', action='store_true', help='Actualizar resultados de los juegos de ayer')
    parser.add_argument('--status', action='store_true', help='Mostrar estado actual de la empresa')
    parser.add_argument('--compare', action='store_true', help='Comparar rendimiento de analistas')
    parser.add_argument('--create-ticket', action='store_true', help='Crear un ticket con predicciones del día')
    parser.add_argument('--list-tickets', action='store_true', help='Listar todos los tickets creados')
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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()