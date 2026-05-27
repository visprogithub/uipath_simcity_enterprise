"""
Phase detector: determines the current game phase based on metrics and building states.
"""
import logging
from collections import deque
from typing import Deque, List

from models.building import Building, BuildingStatus
from models.state import GamePhase, SimulationMetrics

logger = logging.getLogger(__name__)

# History length for trending analysis
TREND_WINDOW = 10


class PhaseDetector:
    def __init__(self) -> None:
        self._stability_history: Deque[float] = deque(maxlen=TREND_WINDOW)
        self._previous_phase: GamePhase = GamePhase.healthy
        self._ticks_in_crisis: int = 0
        self._ticks_recovering: int = 0

    def detect_phase(
        self, metrics: SimulationMetrics, buildings: List[Building]
    ) -> GamePhase:
        """Determine the current game phase."""
        # Track stability history for trend analysis
        self._stability_history.append(metrics.operationalStability)

        # Check for collapsed state first (most severe)
        if (
            metrics.operationalStability < 15
            and metrics.serviceAvailability < 20
        ):
            self._ticks_in_crisis = 0
            phase = GamePhase.collapsed
            self._previous_phase = phase
            return phase

        # Count building states
        offline_count = sum(1 for b in buildings if b.status == BuildingStatus.offline)
        critical_count = sum(1 for b in buildings if b.status == BuildingStatus.critical)
        degraded_count = sum(1 for b in buildings if b.status == BuildingStatus.degraded)

        # Check critical buildings specifically
        hospital = next((b for b in buildings if b.id == "hospital"), None)
        pharmacy = next((b for b in buildings if b.id == "pharmacy"), None)
        cloud = next((b for b in buildings if b.id == "cloud_datacenter"), None)

        critical_services_down = (
            (hospital and hospital.status in (BuildingStatus.offline, BuildingStatus.critical)) or
            (pharmacy and pharmacy.status in (BuildingStatus.offline, BuildingStatus.critical))
        )

        cascade_active = offline_count >= 2 or (cloud and cloud.health < 30)

        # Crisis detection
        in_crisis = (
            (metrics.operationalStability < 40 and metrics.serviceAvailability < 40) or
            (critical_services_down and offline_count >= 1) or
            (cascade_active and critical_count >= 2) or
            (metrics.humanStrain > 85 and metrics.operationalStability < 50) or
            offline_count >= 3
        )

        if in_crisis:
            self._ticks_in_crisis += 1
            self._ticks_recovering = 0
            phase = GamePhase.crisis
            self._previous_phase = phase
            return phase

        # Recovery detection (transitioning up from crisis)
        was_in_crisis = self._previous_phase in (GamePhase.crisis, GamePhase.collapsed)
        trending_up = self._is_trending_up()

        if was_in_crisis and trending_up:
            self._ticks_recovering += 1
            self._ticks_in_crisis = 0
            # Stay in recovering until fully healthy
            if (
                metrics.operationalStability > 70
                and metrics.serviceAvailability > 70
                and self._ticks_recovering >= 5
            ):
                # Graduate to healthy
                self._ticks_recovering = 0
                phase = GamePhase.healthy
            else:
                phase = GamePhase.recovering
            self._previous_phase = phase
            return phase

        # Degrading detection
        degrading = (
            (metrics.operationalStability < 70 or metrics.serviceAvailability < 70) or
            degraded_count >= 2 or
            critical_count >= 1 or
            metrics.humanStrain > 60
        )

        if degrading:
            self._ticks_in_crisis = 0
            phase = GamePhase.degrading
            self._previous_phase = phase
            return phase

        # Healthy: all metrics solid
        self._ticks_in_crisis = 0
        self._ticks_recovering = 0
        phase = GamePhase.healthy
        self._previous_phase = phase
        return phase

    def _is_trending_up(self) -> bool:
        """Check if operational stability is trending upward over recent history."""
        if len(self._stability_history) < 3:
            return False
        recent = list(self._stability_history)[-5:]
        if len(recent) < 2:
            return False
        # Simple linear trend check
        first_half = sum(recent[: len(recent) // 2]) / (len(recent) // 2)
        second_half = sum(recent[len(recent) // 2:]) / (len(recent) - len(recent) // 2)
        return second_half > first_half + 1.0

    def _is_trending_down(self) -> bool:
        """Check if operational stability is trending downward."""
        if len(self._stability_history) < 5:
            return False
        recent = list(self._stability_history)[-5:]
        first_half = sum(recent[:2]) / 2
        second_half = sum(recent[-2:]) / 2
        return second_half < first_half - 2.0

    @property
    def ticks_in_crisis(self) -> int:
        return self._ticks_in_crisis

    @property
    def previous_phase(self) -> GamePhase:
        return self._previous_phase

    @property
    def stability_trend(self) -> float:
        """Return the slope of stability over the last TREND_WINDOW ticks."""
        if len(self._stability_history) < 2:
            return 0.0
        history = list(self._stability_history)
        n = len(history)
        if n < 2:
            return 0.0
        # Simple slope: last - first over window
        return (history[-1] - history[0]) / n
