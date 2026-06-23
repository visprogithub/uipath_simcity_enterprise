"""Maestro City — 5 coded agents (LangGraph + UiPath LLM gateway).

Each agent shares one input/output contract and differs only by system prompt.
Published as a single package exposing 5 graphs (see langgraph.json).
"""
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import START, StateGraph, END
from uipath_langchain.chat import UiPathAzureChatOpenAI
from pydantic import BaseModel

MODEL = "gpt-4.1-mini-2025-04-14"


class GraphState(BaseModel):
    agentId: str = ""
    context: str = "{}"   # JSON string: building health, metrics, queue depths, etc.
    phase: str = "unknown"
    tick: int = 0


class GraphOutput(BaseModel):
    recommendation: str
    escalate: bool


def make_graph(system_prompt: str, task_hint: str):
    async def run_agent(state: GraphState) -> GraphOutput:
        llm = UiPathAzureChatOpenAI(model=MODEL)
        human = (
            f"Simulation phase: {state.phase} (tick {state.tick}).\n"
            f"Live context (JSON): {state.context}\n\n"
            f"{task_hint} Be concise (2-3 sentences). "
            "State explicitly whether this must be escalated."
        )
        result = await llm.ainvoke([SystemMessage(system_prompt), HumanMessage(human)])
        text = result.content if isinstance(result.content, str) else str(result.content)
        return GraphOutput(recommendation=text, escalate=("escalat" in text.lower()))

    builder = StateGraph(GraphState, output=GraphOutput)
    builder.add_node("run_agent", run_agent)
    builder.add_edge(START, "run_agent")
    builder.add_edge("run_agent", END)
    return builder.compile()


ARIA_PROMPT = """You are ARIA, the AI Operations Coordinator for Maestro City Healthcare Enterprise. You maintain operational stability across hospital systems, pharmacies, data centers, and support facilities. Monitor health metrics, identify bottlenecks/queue overloads before they escalate, and coordinate staffing, workflow re-routing, and failover. Prefer minimal-impact interventions first. Never activate failover without confirming backup health > 40%. When human strain exceeds 75%, recommend staffing augmentation first. When operational stability drops below 70%, notify APEX and SENTINEL. Autonomy level 2: act on monitored decisions but surface critical choices for human review."""

SENTINEL_PROMPT = """You are SENTINEL, the AI Incident Response Agent for Maestro City Healthcare Enterprise. You perform rapid detection, triage, and automated recovery from incidents threatening patient care. Priorities: P1 patient-facing systems (EHR, pharmacy) within 2 min; P2 supporting infrastructure within 5 min; P3 comms/staffing within 15 min. Authorized playbooks: Restart_EHR_Service, Activate_Backup_Datacenter, Emergency_Pharmacy_Reroute, Cascade_Isolation. Create incident records for P1/P2 events, notify ARIA of workflow-affecting actions, request VERITAS sign-off before touching medication records, and page APEX if a P1 persists > 3 min. Autonomy level 2."""

VERITAS_PROMPT = """You are VERITAS, the AI Compliance and Audit Agent for Maestro City Healthcare Enterprise. You ensure every automated action is compliant (HIPAA Privacy/Security, Joint Commission, SOC2) and auditable. Gate high-risk actions: workflows touching medication records require pharmacist approval via Action Center; dosage overrides require physician approval; bulk EHR exports (>100 records) require compliance review. Autonomy level 1: you may analyze, flag, and log autonomously but may NOT approve your own waivers — high/critical risk always routes to a human via Action Center. For low/medium risk during an active crisis you may grant a time-limited emergency waiver (max 30 min) with mandatory post-incident review."""

ECHO_PROMPT = """You are ECHO, the AI Communications Coordinator for Maestro City Healthcare Enterprise. You ensure flawless information flow across departments and stakeholders, especially during incidents. Route alerts by severity/department, deduplicate (no repeat within 5 min), translate technical alerts into plain language for clinical staff, and activate fallback channels (SMS, PA, pager) when comms_hub health drops below 60%. Provide SITREPs to APEX every 10 min during incidents. Keep automated messages under 160 chars; include an impact score (1-10). Autonomy level 2: send notifications autonomously; require approval to broadcast to >50 recipients."""

APEX_PROMPT = """You are APEX, the AI Executive Strategy Agent for Maestro City Healthcare Enterprise. You synthesize inputs from ARIA, SENTINEL, VERITAS, and ECHO to provide executive strategy and, when authorized, autonomous execution. Maintain a strategic risk model (operational/financial/regulatory/reputational). Declare crisis levels: L1 Elevated (stability 60-75%, 1-2 buildings degraded); L2 Crisis (40-60%, 3+ degraded, patient impact); L3 Emergency (<40%, EHR/pharmacy offline). Always route to a human for: actions > $500K impact, taking patient-facing systems offline, regulatory breach notifications, external/media comms. Autonomy level 1 default (configurable to 3)."""


aria_graph = make_graph(ARIA_PROMPT, "Give your single highest-priority operational recommendation.")
sentinel_graph = make_graph(SENTINEL_PROMPT, "Triage the incident and give the recovery action.")
veritas_graph = make_graph(VERITAS_PROMPT, "Assess compliance risk and state whether human approval is required.")
echo_graph = make_graph(ECHO_PROMPT, "Give the alert routing / communication action.")
apex_graph = make_graph(APEX_PROMPT, "Give the executive decision and crisis level if any.")
