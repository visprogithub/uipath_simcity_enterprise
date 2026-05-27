"""
Escalation Router: maps simulation events to UiPath processes.
"""
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from models.state import SimulationEventType, UiPathJob

if TYPE_CHECKING:
    from orchestration.uipath_client import UiPathClient

logger = logging.getLogger(__name__)

# Maps (event_type, optional_context_key) -> process_name
_EVENT_PROCESS_MAP: Dict[str, Dict[str, str]] = {
    SimulationEventType.outage_started.value: {
        "cloud_datacenter": "Incident_Escalation",
        "hospital": "Incident_Escalation",
        "pharmacy": "Incident_Escalation",
        "_default": "Incident_Escalation",
    },
    SimulationEventType.approval_required.value: {
        "_default": "Approval_Chain",
    },
    SimulationEventType.staffing_overload.value: {
        "_default": "Emergency_Staffing",
    },
    SimulationEventType.cascade_propagated.value: {
        "crisis": "Crisis_Response",
        "_default": "Crisis_Response",
    },
    SimulationEventType.trust_drop.value: {
        "_default": "Trust_Recovery_Protocol",
    },
    SimulationEventType.uipath_job_completed.value: {
        "_default": None,  # no auto-response
    },
}


class EscalationRouter:
    def __init__(self, uipath_client: "UiPathClient") -> None:
        self.client = uipath_client

    async def route_escalation(
        self,
        event_type: str,
        context: Dict[str, Any],
    ) -> Optional[UiPathJob]:
        """
        Route a simulation event to the appropriate UiPath process.
        Returns the started UiPathJob or None if not routable.
        """
        process_map = _EVENT_PROCESS_MAP.get(event_type)
        if not process_map:
            logger.debug(f"No escalation mapping for event type: {event_type}")
            return None

        # Try to find a specific mapping based on context
        process_name: Optional[str] = None

        # Check building-specific mappings
        building_id = context.get("buildingId") or context.get("building_id", "")
        if building_id and building_id in process_map:
            process_name = process_map[building_id]
        else:
            # Check phase-specific mappings
            phase = context.get("phase", "")
            if phase and phase in process_map:
                process_name = process_map[phase]
            else:
                process_name = process_map.get("_default")

        if not process_name:
            logger.debug(f"No process name resolved for {event_type} with context {context}")
            return None

        logger.info(
            f"Escalation routing: {event_type} -> {process_name} "
            f"(context: {list(context.keys())})"
        )

        job = await self.client.start_job(process_name, {
            "eventType": event_type,
            "context": context,
            "routedBy": "EscalationRouter",
        })

        if job:
            logger.info(f"Escalation job started: {process_name} (id={job.id})")
        else:
            logger.warning(f"Failed to start escalation job: {process_name}")

        return job

    def get_process_for_event(
        self, event_type: str, context: Dict[str, Any]
    ) -> Optional[str]:
        """Preview which process would be triggered without starting it."""
        process_map = _EVENT_PROCESS_MAP.get(event_type, {})
        building_id = context.get("buildingId", "")
        phase = context.get("phase", "")

        if building_id in process_map:
            return process_map[building_id]
        if phase in process_map:
            return process_map[phase]
        return process_map.get("_default")

    @staticmethod
    def get_all_mappings() -> Dict[str, Dict[str, str]]:
        """Return the full event-to-process mapping for inspection."""
        return _EVENT_PROCESS_MAP.copy()
