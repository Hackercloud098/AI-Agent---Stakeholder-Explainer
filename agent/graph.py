from __future__ import annotations

import json
from langgraph.graph import StateGraph, END
#from langchain_google_vertexai import ChatVertexAI
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, TypeAdapter
from typing import Type, TypeVar

from agent.schemas import AgentState, ExtractedFacts, StakeholderBrief
from agent.prompts import FACT_EXTRACT_PROMPT, BRIEF_PROMPT

import os
from langchain_core.exceptions import LangChainException
import re

T = TypeVar("T", bound=BaseModel)

def strip_json_fences(text: str) -> str:
    if not isinstance(text, str):
        return text
    t = text.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", t, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else t

def extract_first_json_object(text: str) -> str:
    """
    If model returns extra text, find the first {...} JSON object by brace matching.
    """
    t = text.strip()
    start = t.find("{")
    if start == -1:
        return t
    depth = 0
    for i in range(start, len(t)):
        if t[i] == "{":
            depth += 1
        elif t[i] == "}":
            depth -= 1
            if depth == 0:
                return t[start : i + 1]
    return t[start:]  # best effort

def parse_and_validate(model_cls: Type[T], raw: str) -> T:
    """
    1) Remove ```json fences
    2) Extract first JSON object
    3) json.loads
    4) Pydantic validate (handles schema)
    """
    cleaned = strip_json_fences(raw)
    cleaned = extract_first_json_object(cleaned)

    data = json.loads(cleaned)  # will raise if still invalid
    return TypeAdapter(model_cls).validate_python(data)

def _json_schema(model_cls) -> str:
    return json.dumps(model_cls.model_json_schema(), indent=2)


def make_llm():
    # env var -> API_KEY
    return ChatGoogleGenerativeAI(
            model="models/gemini-2.5-flash",
            temperature=0.2,
            #location=os.getenv("GOOGLE_CLOUD_REGION", "europe-west2"),
            #project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            google_api_key=os.getenv("GEMINI_API_KEY"),
        )


def classify_node(state: AgentState) -> AgentState:
    state.debug["category"] = state.inp.type
    return state


def extract_facts_node(state: AgentState) -> AgentState:
    try:
        llm = make_llm()
        prompt = FACT_EXTRACT_PROMPT.format(schema=_json_schema(ExtractedFacts))
        content = {
            "type": state.inp.type,
            "system": state.inp.system,
            "timestamp_utc": state.inp.timestamp_utc,
            "signals": state.inp.signals.model_dump(),
            "raw_text": state.inp.raw_text,
            "context": state.inp.context.model_dump(),
        }
        msg = f"{prompt}\n\nINPUT:\n{json.dumps(content, indent=2)}"
        resp = llm.invoke(msg).content

        # robust parsing + validation
        state.facts = parse_and_validate(ExtractedFacts, resp)
        state.debug["mode"] = "llm"
        state.debug["model"] = "models/gemini-2.5-flash"
        return state

    except Exception as e:
        # Fallback for demos when API quota/billing isn't enabled
        state.debug["llm_error"] = str(e)
        state.facts = ExtractedFacts(
            category=state.inp.type,
            severity="high" if (state.inp.signals.error_rate or 0) >= 0.05 else "medium",
            timeframe=f"around {state.inp.timestamp_utc}",
            symptoms=[
                f"Error rate {state.inp.signals.error_rate}" if state.inp.signals.error_rate is not None else "Errors observed",
                f"p95 latency {state.inp.signals.p95_latency_ms} ms" if state.inp.signals.p95_latency_ms is not None else "Latency degradation"
            ],
            likely_causes=[state.inp.context.recent_change or "Recent change suspected"],
            affected_surfaces=["API/service endpoint"],
            blockers=[state.inp.context.customer_impact_hint or "User workflow impacted"]
        )
        return state



def build_brief_node(state: AgentState) -> AgentState:
    try:
        llm = make_llm()
        prompt = BRIEF_PROMPT.format(schema=_json_schema(StakeholderBrief))
        content = {
            "system": state.inp.system,
            "timestamp_utc": state.inp.timestamp_utc,
            "signals": state.inp.signals.model_dump(),
            "context": state.inp.context.model_dump(),
            "facts": state.facts.model_dump() if state.facts else None,
            "raw_text": state.inp.raw_text,
        }
        msg = f"{prompt}\n\nINPUT:\n{json.dumps(content, indent=2)}"
        resp = llm.invoke(msg).content

        state.brief = parse_and_validate(StakeholderBrief, resp)
        state.debug["mode"] = "llm"
        state.debug["model"] = "models/gemini-2.5-flash"
        return state
    except Exception as e:
        state.debug["llm_error"] = str(e)
        er = state.inp.signals.error_rate
        p95 = state.inp.signals.p95_latency_ms

        state.brief = StakeholderBrief(
            headline=f"{state.inp.system}: operational degradation detected",
            summary_non_technical=(
                "We’re seeing a service degradation likely linked to a recent change. "
                "Users may experience failures or slow responses while we mitigate."
            ),
            business_impact={
                "who_is_affected": "Users of the service / downstream teams",
                "what_is_blocked": state.inp.context.customer_impact_hint or "Core workflow reliability reduced",
                "urgency": "high" if (er or 0) >= 0.05 else "medium",
            },
            recommended_actions=[
                {"action": "Rollback or hotfix the most recent change", "owner": "Engineering", "urgency": "today"},
                {"action": "Add deployment guardrails (dependency check / smoke test)", "owner": "ML Platform", "urgency": "this_week"},
            ],
            success_metrics=[
                "Error rate < 1% for 30 minutes" if er is not None else "Errors return to baseline",
                "p95 latency returns to baseline" if p95 is not None else "Latency returns to baseline",
            ],
            assumptions=[
                "Signals provided reflect production impact",
                "Recent change is causally related (needs confirmation)",
            ],
            confidence=0.55,
        )
        return state



def build_graph():
    g = StateGraph(AgentState)
    g.add_node("classify", classify_node)
    g.add_node("extract_facts", extract_facts_node)
    g.add_node("build_brief", build_brief_node)

    g.set_entry_point("classify")
    g.add_edge("classify", "extract_facts")
    g.add_edge("extract_facts", "build_brief")
    g.add_edge("build_brief", END)

    return g.compile()
