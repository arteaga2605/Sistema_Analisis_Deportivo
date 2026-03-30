# analista_tickets.py
"""
Analista especializado en evaluar tickets activos.
Analiza la probabilidad real de acierto del ticket basándose en:
- Estadísticas avanzadas de los equipos involucrados
- Sentimiento real de redes sociales (vía Xpoz + VADER)
- Probabilidades combinadas vs cuota ofrecida
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import requests
import json
import time
import uuid

from models import Estado, Prediccion
from config import (
    UMBRAL_PROBABILIDAD, USE_MULTI_PROVIDER, 
    ENABLE_SOCIAL_SENTIMENT, XPOZ_TOKEN
)
from models.estado import EvaluacionTicket

if USE_MULTI_PROVIDER:
    from data_providers import DataProviderManager
    data_manager = DataProviderManager()

# Intentar importar VADER para análisis de sentimiento real
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    print("⚠️ vaderSentiment no instalado. Para análisis real: pip install vaderSentiment")


class RealSentimentAnalyzer:
    """
    Analiza sentimiento real de redes sociales usando Xpoz (datos) y VADER (análisis).
    Xpoz proporciona acceso a millones de posts sin API key.
    VADER analiza el sentimiento optimizado para redes sociales.
    """
    
    def __init__(self):
        self.xpoz_token = XPOZ_TOKEN
        self.vader = SentimentIntensityAnalyzer() if VADER_AVAILABLE else None
        self._cache = {}
    
    def _query_xpoz(self, query: str, limit: int = 50) -> List[str]:
        """
        Consulta Xpoz MCP para obtener posts reales sobre un tema.
        Xpoz requiere token personal (gratuito) pero no API key.
        """
        if not self.xpoz_token:
            return []
        
        try:
            # Xpoz MCP endpoint (según documentación)
            url = "https://mcp.xpoz.ai/query"
            headers = {"Authorization": f"Bearer {self.xpoz_token}"}
            payload = {
                "query": query,
                "limit": limit,
                "platforms": ["twitter", "reddit", "facebook"]
            }
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                posts = data.get("posts", [])
                return [post.get("text", "") for post in posts]
        except Exception as e:
            print(f"  ⚠️ Error consultando Xpoz: {e}")
        return []
    
    def analyze_sentiment(self, team_name: str, keywords: List[str] = None) -> Dict[str, Any]:
        """
        Analiza sentimiento real para un equipo en redes sociales.
        Retorna:
        - score: -1 a 1 (negativo a positivo)
        - confidence: confianza del análisis (0-1)
        - sample_size: número de posts analizados
        """
        if not VADER_AVAILABLE:
            return {'score': 0, 'confidence': 0, 'sample_size': 0, 'source': 'simulado'}
        
        cache_key = f"{team_name}_{date.today()}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Construir consulta para Xpoz
        if keywords:
            query = f"{team_name} {' '.join(keywords)}"
        else:
            query = f"{team_name} fan sentiment"
        
        # Obtener posts reales
        posts = self._query_xpoz(query, limit=30)
        
        if not posts:
            return {'score': 0, 'confidence': 0, 'sample_size': 0, 'source': 'no_data'}
        
        # Analizar cada post con VADER (optimizado para redes sociales)
        compound_scores = []
        for post in posts:
            sentiment = self.vader.polarity_scores(post)
            compound_scores.append(sentiment['compound'])
        
        avg_score = sum(compound_scores) / len(compound_scores)
        confidence = min(0.9, len(posts) / 100)  # Más posts = más confianza
        
        result = {
            'score': avg_score,
            'confidence': confidence,
            'sample_size': len(posts),
            'source': 'xpoz_vader',
            'positive_percent': sum(1 for s in compound_scores if s > 0.05) / len(compound_scores) * 100,
            'negative_percent': sum(1 for s in compound_scores if s < -0.05) / len(compound_scores) * 100,
            'neutral_percent': sum(1 for s in compound_scores if -0.05 <= s <= 0.05) / len(compound_scores) * 100
        }
        
        self._cache[cache_key] = result
        return result


class TicketAnalyst:
    """
    Analista especializado en evaluar tickets activos.
    Calcula la probabilidad real de acierto considerando estadísticas y sentimiento social.
    """
    
    def __init__(self):
        self.nombre = "Analista de Tickets"
        self.sentiment_analyzer = RealSentimentAnalyzer() if ENABLE_SOCIAL_SENTIMENT else None
    
    def _get_team_stats(self, team_name: str, sport: str, fecha: date) -> Dict[str, Any]:
        """Obtiene estadísticas avanzadas del equipo usando el sistema existente."""
        if not USE_MULTI_PROVIDER:
            return {}
        
        # Obtener récord reciente
        record = data_manager.get_team_recent_record(team_name, fecha, sport)
        total = record['wins'] + record['losses']
        win_pct = record['wins'] / total if total > 0 else 0.5
        
        # Obtener estadísticas adicionales si están disponibles
        stats = data_manager.get_team_stats(team_name, fecha, sport)
        
        # Calcular métricas derivadas
        recent_form = self._get_recent_form(team_name, sport, fecha)
        
        return {
            'record': record,
            'win_pct': win_pct,
            'advanced_stats': stats,
            'recent_form': recent_form
        }
    
    def _get_recent_form(self, team_name: str, sport: str, fecha: date) -> float:
        """Calcula la forma reciente (últimos 5 partidos) como valor entre 0 y 1."""
        start_date = fecha - timedelta(days=7)
        wins = 0
        losses = 0
        current = start_date
        
        while current <= fecha:
            juegos = data_manager.get_games_by_date(current)
            for juego in juegos:
                if juego.get("sport") != sport:
                    continue
                if juego.get("home_team") == team_name or juego.get("away_team") == team_name:
                    if juego.get("status") not in ["finished", "post"]:
                        continue
                    home_score = juego.get("home_score")
                    away_score = juego.get("away_score")
                    if home_score is None or away_score is None:
                        continue
                    is_home = (juego.get("home_team") == team_name)
                    team_score = home_score if is_home else away_score
                    opp_score = away_score if is_home else home_score
                    if team_score > opp_score:
                        wins += 1
                    else:
                        losses += 1
            current += timedelta(days=1)
        
        total = wins + losses
        return wins / total if total > 0 else 0.5
    
    def _get_social_sentiment(self, team_name: str, sport: str) -> Dict[str, Any]:
        """Obtiene sentimiento real de redes sociales para el equipo."""
        if not self.sentiment_analyzer:
            return {'score': 0, 'confidence': 0, 'sample_size': 0, 'source': 'simulado'}
        
        # Keywords relevantes según deporte
        keywords_map = {
            'mlb': ['baseball', 'mlb', 'game'],
            'nfl': ['football', 'nfl', 'touchdown'],
            'nba': ['basketball', 'nba', 'hoops'],
            'nhl': ['hockey', 'nhl', 'puck'],
            'soccer': ['football', 'soccer', 'goal']
        }
        keywords = keywords_map.get(sport, ['game', 'sport', 'team'])
        
        return self.sentiment_analyzer.analyze_sentiment(team_name, keywords)
    
    def _calculate_ticket_probability(self, ticket) -> Tuple[float, List[Dict]]:
        """
        Calcula la probabilidad real de que el ticket acierte.
        Retorna (probabilidad, detalles_por_partido)
        """
        if not ticket.predicciones:
            return 0.0, []
        
        detalles = []
        prob_total = 1.0
        
        for pred in ticket.predicciones:
            # Obtener estadísticas de los equipos
            stats_local = self._get_team_stats(pred.equipo_local, pred.deporte.split()[1] if ' ' in pred.deporte else pred.deporte, pred.fecha)
            stats_visitante = self._get_team_stats(pred.equipo_visitante, pred.deporte.split()[1] if ' ' in pred.deporte else pred.deporte, pred.fecha)
            
            # Obtener sentimiento social real (no simulado)
            sentimiento_local = self._get_social_sentiment(pred.equipo_local, pred.deporte.split()[1] if ' ' in pred.deporte else pred.deporte)
            sentimiento_visitante = self._get_social_sentiment(pred.equipo_visitante, pred.deporte.split()[1] if ' ' in pred.deporte else pred.deporte)
            
            # Calcular factor de forma reciente
            form_local = stats_local.get('recent_form', 0.5)
            form_visitante = stats_visitante.get('recent_form', 0.5)
            
            # Factor de sentimiento social (diferencia entre equipos)
            sentimiento_factor = sentimiento_local['score'] - sentimiento_visitante['score']
            sentimiento_factor = max(-0.2, min(0.2, sentimiento_factor))
            
            # Probabilidad base (del analista original)
            prob_base = pred.probabilidad
            
            # Ajuste por forma reciente (25% peso)
            form_diff = form_local - form_visitante
            if pred.ganador_predicho == pred.equipo_local:
                form_adjust = form_diff * 0.15
            else:
                form_adjust = -form_diff * 0.15
            
            # Ajuste por sentimiento social (20% peso, solo si hay datos reales)
            if sentimiento_local['sample_size'] > 0:
                sent_adjust = sentimiento_factor * 0.20
                sentimiento_texto = f"real (Xpoz+VADER): {sentimiento_local['score']:.2f} vs {sentimiento_visitante['score']:.2f}"
            else:
                sent_adjust = 0
                sentimiento_texto = "sin datos suficientes"
            
            # Probabilidad final del partido
            prob_partido = prob_base + form_adjust + sent_adjust
            prob_partido = max(0.05, min(0.95, prob_partido))
            
            detalles.append({
                'partido': f"{pred.equipo_local} vs {pred.equipo_visitante}",
                'prediccion': pred.ganador_predicho,
                'probabilidad_original': prob_base,
                'probabilidad_ajustada': prob_partido,
                'factor_forma': form_adjust,
                'factor_sentimiento': sent_adjust,
                'sentimiento_local': sentimiento_local,
                'sentimiento_visitante': sentimiento_visitante,
                'sentimiento_texto': sentimiento_texto
            })
            
            prob_total *= prob_partido
        
        return prob_total, detalles
    
    def analizar_tickets_activos(self) -> List[Dict[str, Any]]:
        """
        Analiza todos los tickets pendientes y calcula su probabilidad real de acierto.
        Retorna lista con análisis detallado por ticket.
        """
        estado = Estado()
        tickets_pendientes = [t for t in estado.tickets if t.estado == "pendiente"]
        
        if not tickets_pendientes:
            print("No hay tickets pendientes para analizar.")
            return []
        
        resultados = []
        
        print("\n" + "="*80)
        print(f"🎫 ANÁLISIS DE TICKETS ACTIVOS - {self.nombre}")
        print("="*80)
        
        for ticket in tickets_pendientes:
            print(f"\n📋 Ticket: {ticket.id_ticket}")
            print(f"   Fecha: {ticket.fecha_creacion}")
            print(f"   Cuota: {ticket.odds:.2f} | Monto: {ticket.monto_total:.2f}")
            print("-" * 50)
            
            # Calcular probabilidad real
            prob_real, detalles = self._calculate_ticket_probability(ticket)
            
            # Calcular valor esperado
            valor_esperado = (prob_real * ticket.odds) - 1
            esperanza_ganancia = (prob_real * ticket.monto_total * (ticket.odds - 1)) - ((1 - prob_real) * ticket.monto_total)
            
            # Mostrar resultados por partido
            for detalle in detalles:
                ajuste_texto = ""
                if detalle['factor_sentimiento'] != 0:
                    ajuste_texto = f" | Sentimiento: {detalle['sentimiento_texto']}"
                print(f"   🎯 {detalle['partido']}")
                print(f"      Predicción: {detalle['prediccion']}")
                print(f"      Probabilidad original: {detalle['probabilidad_original']*100:.1f}%")
                print(f"      Probabilidad ajustada: {detalle['probabilidad_ajustada']*100:.1f}%")
                print(f"      Factores: Forma: {detalle['factor_forma']*100:.1f}% | Sentimiento: {detalle['factor_sentimiento']*100:.1f}%{ajuste_texto}")
            
            # Mostrar resumen
            print("-" * 50)
            print(f"📊 PROBABILIDAD REAL DEL TICKET: {prob_real*100:.2f}%")
            print(f"🎲 VALOR ESPERADO (EV): {valor_esperado*100:.2f}%")
            
            if valor_esperado > 0:
                print(f"✅ TICKET CON VALOR POSITIVO - Esperanza de ganancia: {esperanza_ganancia:.2f}")
                recomendacion = "CONSERVAR"
            else:
                print(f"❌ TICKET CON VALOR NEGATIVO - Esperanza de pérdida: {esperanza_ganancia:.2f}")
                recomendacion = "RECOMENDADO CANCELAR"
            
            print(f"💡 RECOMENDACIÓN: {recomendacion}")
            print("="*80)
            
            # Guardar la evaluación en el estado
            evaluacion = EvaluacionTicket(
                fecha=date.today(),
                ticket_id=ticket.id_ticket,
                predicciones_ids=[pred.__dict__.get('id', f"pred_{i}") for i, pred in enumerate(ticket.predicciones)],
                probabilidad_real=prob_real,
                recomendacion=recomendacion
            )
            estado.agregar_evaluacion(evaluacion)
            
            resultados.append({
                'ticket_id': ticket.id_ticket,
                'probabilidad_real': prob_real,
                'valor_esperado': valor_esperado,
                'esperanza_ganancia': esperanza_ganancia,
                'recomendacion': recomendacion,
                'detalles': detalles
            })
        
        return resultados