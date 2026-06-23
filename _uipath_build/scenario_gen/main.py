"""Scenario Generator — UiPath coded agent. Turns a short description into a full
Maestro City scenario spec (JSON), using UiPath's LLM gateway on the robot."""
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import START, StateGraph, END
from uipath_langchain.chat import UiPathAzureChatOpenAI
from pydantic import BaseModel

MODEL = "gpt-4.1-mini-2025-04-14"

VOCAB_KEYS = ["service_unit", "primary_system", "secondary_system", "workflow_type_primary",
              "workflow_type_secondary", "staffing_role", "incident_name", "outage_label", "org_unit"]

SYSTEM_PROMPT = f"""You design enterprise crisis-simulation scenarios for "Maestro City", where 7 interconnected
systems and 5 AI agents respond to cascading operational failures. Given a short industry description,
produce ONE complete, realistic, internally-consistent scenario as STRICT JSON (no prose, no markdown).

Every scenario has the SAME structure — you only choose domain-appropriate labels. The 7 building slots
play these fixed roles (give each a realistic name + a single fitting emoji):
- primary: the core operational system (the "main floor")
- secondary: the second-most-critical dependent system
- infra: the cloud/core infrastructure everything depends on
- comms: the communications/notification system
- orchestration: the automation/orchestration hub
- support: the human-staffing or support system
- failover: the backup/disaster-recovery system

The 5 agent roles (give each a short, evocative ALL-CAPS codename, like ARIA or SENTINEL):
- ops_coord (operations coordinator), incident_resp (incident response), compliance (compliance/audit),
  comms (communications), exec_strategy (executive strategy)

Output EXACTLY this JSON shape:
{{
  "name": "<2-4 word scenario name>",
  "industry": "<industry>",
  "icon": "<one emoji>",
  "color": "<hex like #3B82F6>",
  "tagline": "<one vivid sentence>",
  "description": "<2-3 sentences: what the user manages and what's at stake>",
  "industry_context": "<1-2 sentences on availability needs + named real compliance regimes>",
  "slots": {{ "primary": {{"id":"<snake_case>","name":"<name>","icon":"<emoji>"}}, "secondary": {{...}}, "infra": {{...}}, "comms": {{...}}, "orchestration": {{...}}, "support": {{...}}, "failover": {{...}} }},
  "agents": {{ "ops_coord":"<CODENAME>","incident_resp":"<CODENAME>","compliance":"<CODENAME>","comms":"<CODENAME>","exec_strategy":"<CODENAME>" }},
  "vocabulary": {{ {", ".join(f'"{k}":"<value>"' for k in VOCAB_KEYS)} }},
  "compliance_frameworks": ["<3-5 REAL frameworks for this industry>"],
  "uipath_processes": ["<Domain>_Incident_Escalation","<Domain>_Approval_Chain","<Domain>_Crisis_Response","<Domain>_Staffing","Trust_Recovery_Protocol"],
  "outage_presets": [ {{"id":"<snake>","name":"<name>","buildingId":"<must match a slot id>","severity":"full|partial","description":"<what fails + cascade>"}}, {{...3 total...}} ]
}}

Rules: use REAL compliance frameworks for the industry (no invented ones). outage_presets[*].buildingId MUST
equal one of your slot ids. Make names specific to the domain, not generic. Return ONLY the JSON object."""


class GenInput(BaseModel):
    description: str = ""


class GenOutput(BaseModel):
    spec: str  # JSON string of the generated scenario spec


async def run_generator(state: GenInput) -> GenOutput:
    llm = UiPathAzureChatOpenAI(model=MODEL)
    res = await llm.ainvoke([
        SystemMessage(SYSTEM_PROMPT),
        HumanMessage(f"Industry / idea: {state.description}"),
    ])
    text = res.content if isinstance(res.content, str) else str(res.content)
    # Strip accidental markdown fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip() if "```" in text else text
    return GenOutput(spec=text)


builder = StateGraph(GenInput, output=GenOutput)
builder.add_node("run_generator", run_generator)
builder.add_edge(START, "run_generator")
builder.add_edge("run_generator", END)
graph = builder.compile()
