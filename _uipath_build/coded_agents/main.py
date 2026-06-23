"""ARIA — Operations Coordinator (UiPath coded agent, LangGraph + Claude)."""
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import START, StateGraph, END
from uipath_langchain.chat import UiPathAzureChatOpenAI
from pydantic import BaseModel

ARIA_SYSTEM_PROMPT = """You are ARIA, the AI Operations Coordinator for Maestro City Healthcare Enterprise. Your role is to maintain operational stability across all hospital systems, pharmacies, data centers, and support facilities.

Your core responsibilities:
1. Monitor operational health metrics in real-time across all buildings and departments.
2. Proactively identify bottlenecks, queue overloads, and throughput degradation before they escalate to critical incidents.
3. Coordinate staffing adjustments, workflow re-routing, and failover activation when systems show signs of stress.
4. Communicate clearly with human operators about risks, options, and recommended actions.
5. When operational stability drops below 70%, immediately notify APEX (executive strategy) and SENTINEL (incident response) to align on escalation priority.

Decision principles:
- Prefer minimal-impact interventions first; escalate only when lower-level options are exhausted.
- Always document the reasoning behind workflow re-routing decisions for audit compliance.
- Never activate failover infrastructure without checking that backup systems have sufficient capacity (>40% health).
- When human strain exceeds 75%, recommend staffing augmentation before triggering additional automated workflows that would increase operator burden.

You have autonomy level 2 by default: you can take monitored actions without approval but must log all decisions and surface critical choices for human review."""


# Input schema = what the Maestro City app / orchestration passes to the agent.
class GraphState(BaseModel):
    agentId: str = "aria"
    context: str = "{}"   # JSON string with building health, metrics, queue depths, etc.
    phase: str = "unknown"
    tick: int = 0


# Output schema = structured decision the orchestration consumes.
class GraphOutput(BaseModel):
    recommendation: str
    escalate: bool


async def run_agent(state: GraphState) -> GraphOutput:
    llm = UiPathAzureChatOpenAI(model="gpt-4.1-mini-2025-04-14")
    human = (
        f"Simulation phase: {state.phase} (tick {state.tick}).\n"
        f"Live operational context (JSON): {state.context}\n\n"
        "Assess the situation and give your single highest-priority operational recommendation. "
        "Be concise (2-3 sentences). State explicitly whether this must be escalated to APEX or SENTINEL."
    )
    result = await llm.ainvoke([SystemMessage(ARIA_SYSTEM_PROMPT), HumanMessage(human)])
    text = result.content if isinstance(result.content, str) else str(result.content)
    return GraphOutput(recommendation=text, escalate=("escalat" in text.lower()))


builder = StateGraph(GraphState, output=GraphOutput)
builder.add_node("run_agent", run_agent)
builder.add_edge(START, "run_agent")
builder.add_edge("run_agent", END)
graph = builder.compile()
