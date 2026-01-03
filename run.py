import argparse
import json
from agent.graph import build_graph
from agent.schemas import AgentState, ArtifactInput


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to input JSON")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    inp = ArtifactInput(**data)
    state = AgentState(inp=inp)

    app = build_graph()
    out = app.invoke(state)

    final_state = AgentState(**out)

    print("\n=== Stakeholder Brief (JSON) ===")
    print(final_state.brief.model_dump_json(indent=2))

    print("\n=== Debug ===")
    print(final_state.debug)



if __name__ == "__main__":
    main()
