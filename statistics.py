# statistics.py
"""
Módulo para gestionar estadísticas avanzadas de equipos.
Define la clase TeamStats y funciones de cálculo de probabilidad.
"""

from typing import Dict, Any, Optional
import math


class TeamStats:
    """Almacena estadísticas clave de un equipo según el deporte."""
    
    def __init__(self, sport: str, data: Dict[str, Any] = None):
        self.sport = sport
        self.data = data or {}
        
        # MLB stats
        self.era: Optional[float] = None          # ERA del lanzador abridor
        self.whip: Optional[float] = None         # WHIP del lanzador
        self.avg: Optional[float] = None          # AVG del equipo
        self.obp: Optional[float] = None          # OBP del equipo
        self.slg: Optional[float] = None          # SLG del equipo
        self.bullpen_era: Optional[float] = None  # ERA del bullpen
        self.run_diff: Optional[float] = None     # Diferencial de carreras
        
        # Fútbol stats
        self.possession: Optional[float] = None   # Posesión %
        self.xg_for: Optional[float] = None       # Expected Goals a favor
        self.xg_against: Optional[float] = None   # Expected Goals en contra
        self.pass_accuracy: Optional[float] = None # Precisión de pase %
        self.shots_on_target: Optional[float] = None # Tiros al arco / total
        self.recoveries: Optional[float] = None   # Recuperaciones/duelos
        
        # Basketball stats
        self.off_rating: Optional[float] = None   # Offensive Rating
        self.def_rating: Optional[float] = None   # Defensive Rating
        self.ts_percent: Optional[float] = None   # True Shooting %
        self.efg_percent: Optional[float] = None  # Effective FG %
        self.turnovers: Optional[float] = None    # Turnovers por juego
        self.off_rebounds: Optional[float] = None # Rebotes ofensivos %
        self.def_rebounds: Optional[float] = None # Rebotes defensivos %
        
        # NHL stats
        self.gaa: Optional[float] = None          # Goals Against Average
        self.sv_percent: Optional[float] = None   # Save Percentage
        self.high_danger_for: Optional[float] = None  # High-Danger Chances a favor
        self.high_danger_against: Optional[float] = None
        self.corsi: Optional[float] = None        # Corsi (control de posesión)
        self.fenwick: Optional[float] = None
        self.pp_percent: Optional[float] = None   # Power Play %
        self.pk_percent: Optional[float] = None   # Penalty Kill %
        
        # NFL stats
        self.epa_per_play: Optional[float] = None # Expected Points Added por jugada
        self.qbr: Optional[float] = None          # QBR del QB
        self.passer_rating: Optional[float] = None # Passer Rating
        self.yards_per_play_off: Optional[float] = None # Yards por jugada ofensiva
        self.yards_per_play_def: Optional[float] = None # Yards por jugada defensiva
        self.red_zone_eff: Optional[float] = None # Red Zone Efficiency
        self.dvoa_off: Optional[float] = None     # DVOA Ofensiva
        self.dvoa_def: Optional[float] = None     # DVOA Defensiva
        self.dvoa_st: Optional[float] = None      # DVOA Equipos Especiales
        
        if data:
            self._load_data(data)
    
    def _load_data(self, data: Dict[str, Any]):
        """Carga datos desde un diccionario (por ejemplo, respuesta de API)"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización"""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_') and v is not None}
    
    def calculate_win_probability(self, opponent: 'TeamStats') -> float:
        """
        Calcula la probabilidad de victoria frente a un oponente
        utilizando estadísticas específicas del deporte.
        """
        sport = self.sport
        if sport == 'mlb':
            return self._mlb_probability(opponent)
        elif sport == 'soccer':
            return self._soccer_probability(opponent)
        elif sport == 'basketball':
            return self._basketball_probability(opponent)
        elif sport == 'nhl':
            return self._nhl_probability(opponent)
        elif sport == 'nfl':
            return self._nfl_probability(opponent)
        else:
            # Fallback: 50% si no se reconoce el deporte
            return 0.5
    
    def _mlb_probability(self, opp: 'TeamStats') -> float:
        """Cálculo para MLB usando estadísticas clave"""
        def normalize(value, is_lower_better=False):
            if value is None:
                return 0.5
            if is_lower_better:
                if value <= 0:
                    return 1.0
                max_val = 6.0  # ERA rango típico
                if 'whip' in str(value):
                    max_val = 2.0
                norm = max(0, min(1, (max_val - value) / max_val))
            else:
                max_val = 0.35 if 'avg' in str(value) else 0.45 if 'obp' in str(value) else 0.7 if 'slg' in str(value) else 200.0
                norm = max(0, min(1, value / max_val))
            return norm
        
        era_factor_self = normalize(self.era, is_lower_better=True) if self.era is not None else 0.5
        era_factor_opp = normalize(opp.era, is_lower_better=True) if opp.era is not None else 0.5
        era_advantage = era_factor_self - era_factor_opp
        
        whip_factor_self = normalize(self.whip, is_lower_better=True) if self.whip is not None else 0.5
        whip_factor_opp = normalize(opp.whip, is_lower_better=True) if opp.whip is not None else 0.5
        whip_advantage = whip_factor_self - whip_factor_opp
        
        off_self = []
        if self.avg is not None: off_self.append(normalize(self.avg))
        if self.obp is not None: off_self.append(normalize(self.obp))
        if self.slg is not None: off_self.append(normalize(self.slg))
        off_self_avg = sum(off_self) / len(off_self) if off_self else 0.5
        
        off_opp = []
        if opp.avg is not None: off_opp.append(normalize(opp.avg))
        if opp.obp is not None: off_opp.append(normalize(opp.obp))
        if opp.slg is not None: off_opp.append(normalize(opp.slg))
        off_opp_avg = sum(off_opp) / len(off_opp) if off_opp else 0.5
        
        off_advantage = off_self_avg - off_opp_avg
        
        bull_self = normalize(self.bullpen_era, is_lower_better=True) if self.bullpen_era is not None else 0.5
        bull_opp = normalize(opp.bullpen_era, is_lower_better=True) if opp.bullpen_era is not None else 0.5
        bull_advantage = bull_self - bull_opp
        
        run_self = normalize(self.run_diff) if self.run_diff is not None else 0.5
        run_opp = normalize(opp.run_diff) if opp.run_diff is not None else 0.5
        run_advantage = run_self - run_opp
        
        weights = [0.25, 0.20, 0.20, 0.15, 0.20]
        advantages = [era_advantage, whip_advantage, off_advantage, bull_advantage, run_advantage]
        combined = sum(w * a for w, a in zip(weights, advantages))
        prob = 0.5 + combined * 0.25
        prob = max(0.05, min(0.95, prob))
        return prob
    
    def _soccer_probability(self, opp: 'TeamStats') -> float:
        """Cálculo para fútbol"""
        weights = [0.20, 0.30, 0.15, 0.20, 0.15]
        
        def norm(value, max_val=100):
            if value is None:
                return 0.5
            return max(0, min(1, value / max_val))
        
        pos_self = norm(self.possession)
        pos_opp = norm(opp.possession)
        pos_adv = pos_self - pos_opp
        
        xg_self = norm(self.xg_for, max_val=3) if self.xg_for is not None else 0.5
        xg_opp = norm(opp.xg_against, max_val=3) if opp.xg_against is not None else 0.5
        xg_adv = xg_self - xg_opp
        
        pass_self = norm(self.pass_accuracy)
        pass_opp = norm(opp.pass_accuracy)
        pass_adv = pass_self - pass_opp
        
        shots_self = norm(self.shots_on_target) if self.shots_on_target is not None else 0.5
        shots_opp = norm(opp.shots_on_target) if opp.shots_on_target is not None else 0.5
        shots_adv = shots_self - shots_opp
        
        rec_self = norm(self.recoveries) if self.recoveries is not None else 0.5
        rec_opp = norm(opp.recoveries) if opp.recoveries is not None else 0.5
        rec_adv = rec_self - rec_opp
        
        advantages = [pos_adv, xg_adv, pass_adv, shots_adv, rec_adv]
        combined = sum(w * a for w, a in zip(weights, advantages))
        prob = 0.5 + combined * 0.25
        return max(0.05, min(0.95, prob))
    
    def _basketball_probability(self, opp: 'TeamStats') -> float:
        """Cálculo para baloncesto"""
        weights = [0.25, 0.20, 0.15, 0.15, 0.15, 0.10]
        
        def norm(value, is_lower_better=False):
            if value is None:
                return 0.5
            if is_lower_better:
                max_val = 20
                return max(0, min(1, (max_val - value) / max_val))
            else:
                max_val = 120 if 'rating' in str(value) else 1.0
                return max(0, min(1, value / max_val))
        
        off_self = norm(self.off_rating)
        off_opp = norm(opp.off_rating)
        off_adv = off_self - off_opp
        
        def_self = norm(self.def_rating, is_lower_better=True) if self.def_rating is not None else 0.5
        def_opp = norm(opp.def_rating, is_lower_better=True) if opp.def_rating is not None else 0.5
        def_adv = def_self - def_opp
        
        ts_self = norm(self.ts_percent)
        ts_opp = norm(opp.ts_percent)
        ts_adv = ts_self - ts_opp
        
        efg_self = norm(self.efg_percent)
        efg_opp = norm(opp.efg_percent)
        efg_adv = efg_self - efg_opp
        
        to_self = norm(self.turnovers, is_lower_better=True)
        to_opp = norm(opp.turnovers, is_lower_better=True)
        to_adv = to_self - to_opp
        
        reb_self = (norm(self.off_rebounds) + norm(self.def_rebounds)) / 2 if (self.off_rebounds is not None and self.def_rebounds is not None) else 0.5
        reb_opp = (norm(opp.off_rebounds) + norm(opp.def_rebounds)) / 2 if (opp.off_rebounds is not None and opp.def_rebounds is not None) else 0.5
        reb_adv = reb_self - reb_opp
        
        advantages = [off_adv, def_adv, ts_adv, efg_adv, to_adv, reb_adv]
        combined = sum(w * a for w, a in zip(weights, advantages))
        prob = 0.5 + combined * 0.25
        return max(0.05, min(0.95, prob))
    
    def _nhl_probability(self, opp: 'TeamStats') -> float:
        """Cálculo para NHL"""
        weights = [0.20, 0.20, 0.20, 0.20, 0.20]
        
        def norm(value, is_lower_better=False):
            if value is None:
                return 0.5
            if is_lower_better:
                max_val = 3.5
                return max(0, min(1, (max_val - value) / max_val))
            else:
                max_val = 1.0 if 'percent' in str(value) else 100
                return max(0, min(1, value / max_val))
        
        gaa_self = norm(self.gaa, is_lower_better=True)
        gaa_opp = norm(opp.gaa, is_lower_better=True)
        gaa_adv = gaa_self - gaa_opp
        
        sv_self = norm(self.sv_percent)
        sv_opp = norm(opp.sv_percent)
        sv_adv = sv_self - sv_opp
        
        hd_self = (norm(self.high_danger_for) - norm(self.high_danger_against)) / 2 if (self.high_danger_for is not None and self.high_danger_against is not None) else 0
        hd_opp = (norm(opp.high_danger_for) - norm(opp.high_danger_against)) / 2 if (opp.high_danger_for is not None and opp.high_danger_against is not None) else 0
        hd_adv = hd_self - hd_opp
        
        corsi_self = norm(self.corsi) if self.corsi is not None else 0.5
        corsi_opp = norm(opp.corsi) if opp.corsi is not None else 0.5
        corsi_adv = corsi_self - corsi_opp
        
        special_self = (norm(self.pp_percent) + norm(self.pk_percent)) / 2 if (self.pp_percent is not None and self.pk_percent is not None) else 0.5
        special_opp = (norm(opp.pp_percent) + norm(opp.pk_percent)) / 2 if (opp.pp_percent is not None and opp.pk_percent is not None) else 0.5
        special_adv = special_self - special_opp
        
        advantages = [gaa_adv, sv_adv, hd_adv, corsi_adv, special_adv]
        combined = sum(w * a for w, a in zip(weights, advantages))
        prob = 0.5 + combined * 0.25
        return max(0.05, min(0.95, prob))
    
    def _nfl_probability(self, opp: 'TeamStats') -> float:
        """Cálculo para NFL"""
        weights = [0.25, 0.20, 0.20, 0.15, 0.20]
        
        def norm(value, is_lower_better=False):
            if value is None:
                return 0.5
            if 'epa' in str(value):
                return 1 / (1 + math.exp(-value))
            if is_lower_better:
                max_val = 10
                return max(0, min(1, (max_val - value) / max_val))
            max_val = 100
            return max(0, min(1, value / max_val))
        
        epa_self = norm(self.epa_per_play)
        epa_opp = norm(opp.epa_per_play)
        epa_adv = epa_self - epa_opp
        
        qb_self = norm(self.qbr or self.passer_rating)
        qb_opp = norm(opp.qbr or opp.passer_rating)
        qb_adv = qb_self - qb_opp
        
        yds_off_self = norm(self.yards_per_play_off) if self.yards_per_play_off is not None else 0.5
        yds_off_opp = norm(opp.yards_per_play_off) if opp.yards_per_play_off is not None else 0.5
        yds_def_self = norm(self.yards_per_play_def, is_lower_better=True) if self.yards_per_play_def is not None else 0.5
        yds_def_opp = norm(opp.yards_per_play_def, is_lower_better=True) if opp.yards_per_play_def is not None else 0.5
        yds_adv = (yds_off_self - yds_off_opp) + (yds_def_self - yds_def_opp)
        
        red_self = norm(self.red_zone_eff) if self.red_zone_eff is not None else 0.5
        red_opp = norm(opp.red_zone_eff) if opp.red_zone_eff is not None else 0.5
        red_adv = red_self - red_opp
        
        dvoa_self = (norm(self.dvoa_off) + norm(self.dvoa_def) + norm(self.dvoa_st)) / 3 if (self.dvoa_off is not None and self.dvoa_def is not None and self.dvoa_st is not None) else 0.5
        dvoa_opp = (norm(opp.dvoa_off) + norm(opp.dvoa_def) + norm(opp.dvoa_st)) / 3 if (opp.dvoa_off is not None and opp.dvoa_def is not None and opp.dvoa_st is not None) else 0.5
        dvoa_adv = dvoa_self - dvoa_opp
        
        advantages = [epa_adv, qb_adv, yds_adv, red_adv, dvoa_adv]
        combined = sum(w * a for w, a in zip(weights, advantages))
        prob = 0.5 + combined * 0.25
        return max(0.05, min(0.95, prob))
    
    def estimate_score(self, opponent: 'TeamStats') -> tuple:
        """
        Estima el marcador final: (marcador_local, marcador_visitante)
        Devuelve strings como "5-3" o "102-98"
        """
        sport = self.sport
        if sport == 'mlb':
            # Usar run_diff o promedios
            local_runs = self.run_diff / 2 if self.run_diff else 3.5
            away_runs = opponent.run_diff / 2 if opponent.run_diff else 3.5
            # Ajustar por AVG si está disponible
            if self.avg:
                local_runs *= (self.avg / 0.250)
            if opponent.avg:
                away_runs *= (opponent.avg / 0.250)
            local_runs = max(0, int(round(local_runs)))
            away_runs = max(0, int(round(away_runs)))
            return f"{local_runs}", f"{away_runs}"
        elif sport == 'basketball':
            # Usar off_rating como puntos promedio
            local_pts = self.off_rating if self.off_rating else 105
            away_pts = opponent.off_rating if opponent.off_rating else 105
            return f"{int(round(local_pts))}", f"{int(round(away_pts))}"
        elif sport == 'nhl':
            # Goles promedio (si no hay, usar 2.5)
            local_gls = self.xg_for if self.xg_for else 2.5
            away_gls = opponent.xg_for if opponent.xg_for else 2.5
            return f"{int(round(local_gls))}", f"{int(round(away_gls))}"
        elif sport == 'soccer':
            local_gls = self.xg_for if self.xg_for else 1.2
            away_gls = opponent.xg_for if opponent.xg_for else 1.2
            return f"{int(round(local_gls))}", f"{int(round(away_gls))}"
        else:
            return "?", "?"