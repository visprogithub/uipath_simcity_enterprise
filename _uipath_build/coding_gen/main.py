"""Coding Generator — generic UiPath coded agent. Runs a system+user prompt through
UiPath's LLM gateway on the robot and returns the raw text (used by the Coding Agent
feature to generate XAML, entity definitions, and workflow diagnoses)."""
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import START, StateGraph, END
from uipath_langchain.chat import UiPathAzureChatOpenAI
from pydantic import BaseModel

MODEL = "gpt-4.1-mini-2025-04-14"


class GenInput(BaseModel):
    system: str = ""
    user: str = ""


class GenOutput(BaseModel):
    text: str


async def run_llm(state: GenInput) -> GenOutput:
    llm = UiPathAzureChatOpenAI(model=MODEL)
    messages = []
    if state.system:
        messages.append(SystemMessage(state.system))
    messages.append(HumanMessage(state.user))
    res = await llm.ainvoke(messages)
    text = res.content if isinstance(res.content, str) else str(res.content)
    return GenOutput(text=text)


builder = StateGraph(GenInput, output=GenOutput)
builder.add_node("run_llm", run_llm)
builder.add_edge(START, "run_llm")
builder.add_edge("run_llm", END)
graph = builder.compile()
