# animacion.py
"""
Módulo de animación ASCII para mostrar a los empleados trabajando.
Incluye ahora al Analista de Tickets como séptimo empleado.
"""
import os
import time
import sys

def clear_screen():
    """Limpia la pantalla según el sistema operativo."""
    os.system('cls' if os.name == 'nt' else 'clear')

# Arte ASCII de la oficina con SÉPTIMO EMPLEADO (Analista de Tickets)
OFICINA_BASE = """
╔══════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                           🏢 EMPRESA DE ANÁLISIS DEPORTIVO 🏢                                        ║
╠══════════════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                                      ║
║   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          ║
║   │  ANALISTA   │   │  ANALISTA   │   │  GESTOR DE  │   │  CREADOR    │   │  ANALISTA   │          ║
║   │  PRINCIPAL  │   │  AVANZADO   │   │   RIESGO    │   │  DE TICKETS │   │  DE TICKETS │          ║
║   │             │   │             │   │             │   │             │   │             │          ║
║   │    [PC]     │   │    [PC]     │   │   [PIZARRA] │   │   [MEGÁF.]  │   │   [REDES]   │          ║
║   │   {estado1} │   │   {estado2} │   │   {estado3} │   │   {estado4} │   │   {estado5} │          ║
║   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘          ║
║                                                                                                      ║
║   ┌─────────────┐   ┌─────────────┐                                                                 ║
║   │   AUDITOR   │   │  ANALISTA   │                                                                 ║
║   │             │   │   FÚTBOL    │                                                                 ║
║   │  [REPORTES] │   │   [BALÓN]   │                                                                 ║
║   │   {estado6} │   │   {estado7} │                                                                 ║
║   └─────────────┘   └─────────────┘                                                                 ║
║                                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

ESTADOS = {
    'trabajando': '💻 TRABAJANDO',
    'descanso': '☕ DESCANSO',
    'prediciendo': '🔮 PREDICIENDO',
    'ticket': '🎫 CREANDO TICKET',
    'informe': '📊 GENERANDO INFORME',
    'gestion': '📈 ANALIZANDO RIESGO',
    'espera': '🪑 EN ESPERA',
    'futbol': '⚽ ANALIZANDO',
    'analizando_tickets': '🎯 ANALIZANDO'
}

def mostrar_animacion(comando):
    """
    Muestra la oficina con los empleados según el comando ejecutado.
    comando: 'predict', 'ticket', 'report', 'update', 'status', 'compare', 'soccer', 'ticket_analyst'
    """
    # Definir estados según comando
    if comando == 'predict':
        estados = {
            'estado1': ESTADOS['prediciendo'],
            'estado2': ESTADOS['prediciendo'],
            'estado3': ESTADOS['gestion'],
            'estado4': ESTADOS['espera'],
            'estado5': ESTADOS['espera'],
            'estado6': ESTADOS['espera'],
            'estado7': ESTADOS['espera']
        }
    elif comando == 'ticket':
        estados = {
            'estado1': ESTADOS['descanso'],
            'estado2': ESTADOS['descanso'],
            'estado3': ESTADOS['gestion'],
            'estado4': ESTADOS['ticket'],
            'estado5': ESTADOS['espera'],
            'estado6': ESTADOS['espera'],
            'estado7': ESTADOS['espera']
        }
    elif comando == 'report':
        estados = {
            'estado1': ESTADOS['descanso'],
            'estado2': ESTADOS['descanso'],
            'estado3': ESTADOS['gestion'],
            'estado4': ESTADOS['espera'],
            'estado5': ESTADOS['espera'],
            'estado6': ESTADOS['informe'],
            'estado7': ESTADOS['espera']
        }
    elif comando == 'update':
        estados = {
            'estado1': ESTADOS['espera'],
            'estado2': ESTADOS['espera'],
            'estado3': ESTADOS['gestion'],
            'estado4': ESTADOS['espera'],
            'estado5': ESTADOS['espera'],
            'estado6': ESTADOS['espera'],
            'estado7': ESTADOS['espera']
        }
    elif comando == 'status' or comando == 'compare':
        estados = {
            'estado1': ESTADOS['descanso'],
            'estado2': ESTADOS['descanso'],
            'estado3': ESTADOS['descanso'],
            'estado4': ESTADOS['descanso'],
            'estado5': ESTADOS['descanso'],
            'estado6': ESTADOS['descanso'],
            'estado7': ESTADOS['descanso']
        }
    elif comando == 'soccer':
        estados = {
            'estado1': ESTADOS['descanso'],
            'estado2': ESTADOS['descanso'],
            'estado3': ESTADOS['gestion'],
            'estado4': ESTADOS['espera'],
            'estado5': ESTADOS['espera'],
            'estado6': ESTADOS['espera'],
            'estado7': ESTADOS['futbol']
        }
    elif comando == 'ticket_analyst':
        estados = {
            'estado1': ESTADOS['descanso'],
            'estado2': ESTADOS['descanso'],
            'estado3': ESTADOS['gestion'],
            'estado4': ESTADOS['descanso'],
            'estado5': ESTADOS['analizando_tickets'],
            'estado6': ESTADOS['espera'],
            'estado7': ESTADOS['espera']
        }
    else:
        # Por defecto, todos en espera
        estados = {f'estado{i}': ESTADOS['espera'] for i in range(1,8)}

    clear_screen()
    print(OFICINA_BASE.format(**estados))
    print("\n🎬 Los empleados están trabajando...\n")
    time.sleep(2)  # Mostrar animación 2 segundos