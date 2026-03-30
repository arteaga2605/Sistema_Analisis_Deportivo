# animacion.py
"""
Módulo de animación ASCII con estilo mejorado.
Incluye colores (opcional), personajes con emojis, barras de progreso simuladas
y una oficina más detallada para reflejar el estado de los empleados.
"""

import os
import time
import sys

# Intentar importar colorama para colores (opcional)
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    COLORES = True
except ImportError:
    COLORES = False
    # Definir valores dummy para evitar errores
    class Fore: RED = ''; GREEN = ''; YELLOW = ''; CYAN = ''; MAGENTA = ''; WHITE = ''; RESET = ''
    class Back: BLACK = ''; RESET = ''
    class Style: BRIGHT = ''; NORMAL = ''; RESET_ALL = ''


def clear_screen():
    """Limpia la pantalla según el sistema operativo."""
    os.system('cls' if os.name == 'nt' else 'clear')


# Empleados y sus estados posibles (con emojis)
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

# Oficina mejorada: diseño más detallado con divisiones
OFICINA_BASE = """
{fore_cyan}╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                               🏢  EMPRESA DE ANÁLISIS DEPORTIVO  🏢                               ║
╠══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                                                  ║
║   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   ║
║   │   {fore_green}👨‍💻 ANALISTA{fore_reset}   │   │   {fore_green}🧠 ANALISTA{fore_reset}   │   │   {fore_yellow}📈 GESTOR DE{fore_reset}   │   │   {fore_magenta}🎫 CREADOR{fore_reset}   │   │   {fore_cyan}📱 ANALISTA{fore_reset}   │   ║
║   │     PRINCIPAL     │   │     AVANZADO     │   │      RIESGO      │   │   DE TICKETS    │   │   DE TICKETS   │   ║
║   │                   │   │                   │   │                   │   │                   │   │                   │   ║
║   │      {fore_white}[ PC ]{fore_reset}       │   │      {fore_white}[ PC ]{fore_reset}       │   │    {fore_white}[ PIZARRA ]{fore_reset}  │   │    {fore_white}[ MEGÁF. ]{fore_reset}  │   │    {fore_white}[ REDES ]{fore_reset}   │   ║
║   │     {estado1}     │   │     {estado2}     │   │     {estado3}     │   │     {estado4}     │   │     {estado5}     │   ║
║   └─────────────────┘   └─────────────────┘   └─────────────────┘   └─────────────────┘   └─────────────────┘   ║
║                                                                                                                  ║
║   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐                                                ║
║   │   {fore_red}📋 AUDITOR{fore_reset}     │   │   {fore_blue}⚽ ANALISTA{fore_reset}    │   │   {fore_yellow}💡 ASESOR{fore_reset}     │                                                ║
║   │   DE RESULTADOS  │   │     FÚTBOL      │   │   DE APUESTAS    │                                                ║
║   │                   │   │                   │   │                   │                                                ║
║   │   {fore_white}[ REPORTES ]{fore_reset}  │   │    {fore_white}[ BALÓN ]{fore_reset}    │   │    {fore_white}[ DADOS ]{fore_reset}    │                                                ║
║   │     {estado6}     │   │     {estado7}     │   │     {estado8}     │                                                ║
║   └─────────────────┘   └─────────────────┘   └─────────────────┘                                                ║
║                                                                                                                  ║
║   ┌─────────────────┐                                                                                            ║
║   │   {fore_cyan}📊 ANALISTA{fore_reset}   │                                                                                            ║
║   │      EXCEL       │                                                                                            ║
║   │                   │                                                                                            ║
║   │   {fore_white}[ ARCHIVOS ]{fore_reset}  │                                                                                            ║
║   │     {estado9}     │                                                                                            ║
║   └─────────────────┘                                                                                            ║
║                                                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
{fore_reset}
"""

def mostrar_animacion(comando):
    """
    Muestra la oficina con los empleados según el comando ejecutado.
    comando: 'predict', 'ticket', 'report', 'update', 'status', 'compare', 'soccer', 'ticket_analyst', 'evaluate', 'suggest', 'excel'
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
        # Por defecto, todos en espera
        estados = {f'estado{i}': ESTADOS['espera'] for i in range(1,10)}

    # Configurar colores si están disponibles
    fore_cyan = Fore.CYAN if COLORES else ''
    fore_green = Fore.GREEN if COLORES else ''
    fore_yellow = Fore.YELLOW if COLORES else ''
    fore_magenta = Fore.MAGENTA if COLORES else ''
    fore_white = Fore.WHITE if COLORES else ''
    fore_red = Fore.RED if COLORES else ''
    fore_blue = Fore.BLUE if COLORES else ''
    fore_reset = Fore.RESET if COLORES else ''

    clear_screen()
    # Imprimir con formato de colores
    print(OFICINA_BASE.format(
        fore_cyan=fore_cyan,
        fore_green=fore_green,
        fore_yellow=fore_yellow,
        fore_magenta=fore_magenta,
        fore_white=fore_white,
        fore_red=fore_red,
        fore_blue=fore_blue,
        fore_reset=fore_reset,
        **estados
    ))
    # Pequeña barra de progreso animada (simulación)
    print(f"{Fore.CYAN if COLORES else ''}📡 Cargando sistema...{Fore.RESET if COLORES else ''}")
    for i in range(20):
        barra = '█' * (i+1) + '░' * (19-i)
        print(f"\r  [{barra}] {int((i+1)/20*100)}%", end='')
        time.sleep(0.02)
    print("\n")
    time.sleep(0.5)
    print(f"{Fore.GREEN if COLORES else ''}✨ Los empleados están trabajando... ✨{Fore.RESET if COLORES else ''}\n")
    time.sleep(1.5)  # Mostrar animación 1.5 segundos