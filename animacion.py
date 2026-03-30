# animacion.py
"""
Módulo de animación ASCII para mostrar a los empleados trabajando.
Ahora con 9 empleados: 6 analistas + gestor + auditor + asesor + analista excel.
"""
import os
import time

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

OFICINA_BASE = """
╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                           🏢 EMPRESA DE ANÁLISIS DEPORTIVO 🏢                                                    ║
╠══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                                                  ║
║   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                      ║
║   │  ANALISTA   │   │  ANALISTA   │   │  GESTOR DE  │   │  CREADOR    │   │  ANALISTA   │                      ║
║   │  PRINCIPAL  │   │  AVANZADO   │   │   RIESGO    │   │  DE TICKETS │   │  DE TICKETS │                      ║
║   │    [PC]     │   │    [PC]     │   │   [PIZARRA] │   │   [MEGÁF.]  │   │   [REDES]   │                      ║
║   │   {estado1} │   │   {estado2} │   │   {estado3} │   │   {estado4} │   │   {estado5} │                      ║
║   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                      ║
║                                                                                                                  ║
║   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                                       ║
║   │   AUDITOR   │   │  ANALISTA   │   │   ASESOR    │   │  ANALISTA   │                                       ║
║   │             │   │   FÚTBOL    │   │   APUESTAS  │   │   EXCEL     │                                       ║
║   │  [REPORTES] │   │   [BALÓN]   │   │   [DADOS]   │   │   [📊]      │                                       ║
║   │   {estado6} │   │   {estado7} │   │   {estado8} │   │   {estado9} │                                       ║
║   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                                       ║
║                                                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
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
    'analizando_tickets': '🎯 ANALIZANDO',
    'evaluando': '🔍 EVALUANDO',
    'sugiriendo': '💡 SUGIRIENDO',
    'excel': '📊 EXCEL'
}

def mostrar_animacion(comando):
    if comando == 'predict':
        estados = {
            'estado1': ESTADOS['prediciendo'],
            'estado2': ESTADOS['prediciendo'],
            'estado3': ESTADOS['gestion'],
            'estado4': ESTADOS['espera'],
            'estado5': ESTADOS['espera'],
            'estado6': ESTADOS['espera'],
            'estado7': ESTADOS['espera'],
            'estado8': ESTADOS['espera'],
            'estado9': ESTADOS['espera']
        }
    elif comando == 'ticket':
        estados = {
            'estado1': ESTADOS['descanso'],
            'estado2': ESTADOS['descanso'],
            'estado3': ESTADOS['gestion'],
            'estado4': ESTADOS['ticket'],
            'estado5': ESTADOS['espera'],
            'estado6': ESTADOS['espera'],
            'estado7': ESTADOS['espera'],
            'estado8': ESTADOS['espera'],
            'estado9': ESTADOS['espera']
        }
    elif comando == 'report':
        estados = {
            'estado1': ESTADOS['descanso'],
            'estado2': ESTADOS['descanso'],
            'estado3': ESTADOS['gestion'],
            'estado4': ESTADOS['espera'],
            'estado5': ESTADOS['espera'],
            'estado6': ESTADOS['informe'],
            'estado7': ESTADOS['espera'],
            'estado8': ESTADOS['espera'],
            'estado9': ESTADOS['espera']
        }
    elif comando == 'update':
        estados = {
            'estado1': ESTADOS['espera'],
            'estado2': ESTADOS['espera'],
            'estado3': ESTADOS['gestion'],
            'estado4': ESTADOS['espera'],
            'estado5': ESTADOS['espera'],
            'estado6': ESTADOS['espera'],
            'estado7': ESTADOS['espera'],
            'estado8': ESTADOS['espera'],
            'estado9': ESTADOS['espera']
        }
    elif comando in ('status', 'compare'):
        estados = {
            'estado1': ESTADOS['descanso'],
            'estado2': ESTADOS['descanso'],
            'estado3': ESTADOS['descanso'],
            'estado4': ESTADOS['descanso'],
            'estado5': ESTADOS['descanso'],
            'estado6': ESTADOS['descanso'],
            'estado7': ESTADOS['descanso'],
            'estado8': ESTADOS['descanso'],
            'estado9': ESTADOS['descanso']
        }
    elif comando == 'soccer':
        estados = {
            'estado1': ESTADOS['descanso'],
            'estado2': ESTADOS['descanso'],
            'estado3': ESTADOS['gestion'],
            'estado4': ESTADOS['espera'],
            'estado5': ESTADOS['espera'],
            'estado6': ESTADOS['espera'],
            'estado7': ESTADOS['futbol'],
            'estado8': ESTADOS['espera'],
            'estado9': ESTADOS['espera']
        }
    elif comando == 'ticket_analyst':
        estados = {
            'estado1': ESTADOS['descanso'],
            'estado2': ESTADOS['descanso'],
            'estado3': ESTADOS['gestion'],
            'estado4': ESTADOS['descanso'],
            'estado5': ESTADOS['analizando_tickets'],
            'estado6': ESTADOS['espera'],
            'estado7': ESTADOS['espera'],
            'estado8': ESTADOS['espera'],
            'estado9': ESTADOS['espera']
        }
    elif comando == 'evaluate':
        estados = {
            'estado1': ESTADOS['descanso'],
            'estado2': ESTADOS['descanso'],
            'estado3': ESTADOS['gestion'],
            'estado4': ESTADOS['descanso'],
            'estado5': ESTADOS['descanso'],
            'estado6': ESTADOS['descanso'],
            'estado7': ESTADOS['descanso'],
            'estado8': ESTADOS['evaluando'],
            'estado9': ESTADOS['espera']
        }
    elif comando == 'suggest':
        estados = {
            'estado1': ESTADOS['descanso'],
            'estado2': ESTADOS['descanso'],
            'estado3': ESTADOS['gestion'],
            'estado4': ESTADOS['descanso'],
            'estado5': ESTADOS['descanso'],
            'estado6': ESTADOS['descanso'],
            'estado7': ESTADOS['descanso'],
            'estado8': ESTADOS['sugiriendo'],
            'estado9': ESTADOS['espera']
        }
    elif comando == 'excel':
        estados = {
            'estado1': ESTADOS['descanso'],
            'estado2': ESTADOS['descanso'],
            'estado3': ESTADOS['gestion'],
            'estado4': ESTADOS['descanso'],
            'estado5': ESTADOS['descanso'],
            'estado6': ESTADOS['descanso'],
            'estado7': ESTADOS['descanso'],
            'estado8': ESTADOS['descanso'],
            'estado9': ESTADOS['excel']
        }
    else:
        estados = {f'estado{i}': ESTADOS['espera'] for i in range(1,10)}
    
    clear_screen()
    print(OFICINA_BASE.format(**estados))
    print("\n🎬 Los empleados están trabajando...\n")
    time.sleep(2)