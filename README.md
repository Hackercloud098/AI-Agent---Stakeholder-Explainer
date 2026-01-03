# Stakeholder Explainer Agent (AI/ML Ops)

An **agentic AI workflow** that converts AI/ML operational signals  
(logs, metrics, incidents, model updates) into a **business-ready stakeholder brief**.

Designed for teams where **most decision-makers are non-technical**.

---

## Problem

AI and ML systems often fail or degrade in ways that are:

- Technically complex
- Hard to communicate quickly
- Expensive to coordinate during incidents

Engineering teams spend significant time translating:

- **Logs → explanations**
- **Metrics → impact**
- **Fixes → confidence**

This slows decision-making and increases operational risk.

---

## Solution

The **Stakeholder Explainer Agent** automates this translation.

Given technical artefacts (logs, metrics, experiment results), it produces a concise,
forwardable update that answers:

- **What happened?**
- **Why does it matter to the business?**
- **What are we doing next, and who owns it?**
- **How will we know it’s fixed?**

---

## Example Output

**Service instability affecting Debug Copilot users**

A recent deployment introduced a dependency issue causing intermittent service failures.  
This prevents users from reliably accessing troubleshooting reports and increases support load.

**Recommended actions**
- Roll back deployment *(Engineering, today)*
- Add dependency validation to CI *(ML Platform, this week)*

**Success metrics**
- Error rate < 1% for 30 minutes
- p95 latency < 900 ms

**Confidence:** 0.72

---

## Architecture

The agent is implemented as a **LangGraph workflow** with explicit state and schemas.

**Execution flow**
1. Input artefact
2. Classify event
3. Extract decision-relevant facts
4. Generate stakeholder brief

---

### Key Design Choices

- **Explicit state** rather than hidden chains
- **Strict JSON schemas** validated with Pydantic
- **Business-first outputs**, not raw LLM text
- **Easy extensibility** with tools (monitoring APIs, ticketing systems)

---

## Agent Nodes

### Classify
Determines whether the input represents an incident, performance regression, or model update.

### Extract Facts
Captures severity, symptoms, likely causes, affected surfaces, and blockers.

### Build Stakeholder Brief
Produces a plain-English summary, outlines business impact, recommends actions with owners,
and defines success metrics and assumptions.

---

## Running the Demo

### Setup

```bash```
pip install -r requirements.txt
export GEMINI_API_KEY="your_api_key"
python run.py --input examples/incident_01.json

The agent prints a structured stakeholder brief in JSON format.


### Why This Matters?

- Reduces time spent translating technical incidents for leadership and stakeholders
- Improves alignment during high-pressure incidents, reducing confusion and duplicated effort
- Lowers hidden coordination and communication costs during outages and regressions
- Enables faster, more confident decision-making with clear ownership and success criteria

### Future Extensions

- Clarifying-question node when key information is missing (e.g. environment, affected users)
- Live metric retrieval from cloud monitoring systems (e.g. GCP Cloud Monitoring, Prometheus)
- Automatic Jira / incident ticket creation with pre-filled context
- Trend analysis over time by storing briefs to identify recurring failure modes
