from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class Signals(BaseModel):
    error_rate: Optional[float] = None
    p50_latency_ms: Optional[int] = None
    p95_latency_ms: Optional[int] = None
    requests_per_min: Optional[int] = None
    cost_per_1k_requests_usd: Optional[float] = None


class InputContext(BaseModel):
    recent_change: Optional[str] = None
    customer_impact_hint: Optional[str] = None
    environment: Optional[str] = None  # prod/staging
    service_owner: Optional[str] = None


class ArtifactInput(BaseModel):
    type: Literal["incident", "perf_regression", "model_update"]
    system: str
    timestamp_utc: str
    signals: Signals = Field(default_factory=Signals)
    raw_text: str
    context: InputContext = Field(default_factory=InputContext)


class ExtractedFacts(BaseModel):
    category: Literal["incident", "perf_regression", "model_update"]
    severity: Literal["low", "medium", "high", "critical"]
    timeframe: str
    symptoms: List[str]
    likely_causes: List[str]
    affected_surfaces: List[str]  # e.g., API endpoint, UI, batch job
    blockers: List[str]


class RecommendedAction(BaseModel):
    action: str
    owner: str
    urgency: Literal["today", "24h", "this_week"]
    expected_effect: Optional[str] = None


class StakeholderBrief(BaseModel):
    headline: str
    summary_non_technical: str
    business_impact: Dict[str, Any]  # keep flexible
    recommended_actions: List[RecommendedAction]
    success_metrics: List[str]
    assumptions: List[str]
    confidence: float = Field(ge=0.0, le=1.0)


class AgentState(BaseModel):
    inp: ArtifactInput
    facts: Optional[ExtractedFacts] = None
    brief: Optional[StakeholderBrief] = None
    debug: Dict[str, Any] = Field(default_factory=dict)
