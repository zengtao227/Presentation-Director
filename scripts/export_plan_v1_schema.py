from __future__ import annotations

import argparse
import json
from pathlib import Path

from presentation_director_contracts.plan_v1 import PresentationDirectorPlanV1
from presentation_director_contracts.producer_v1 import GovernedPlanProductionInputV1

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = {
    ROOT / "schemas" / "presentation-director-plan-v1.schema.json": PresentationDirectorPlanV1,
    ROOT
    / "schemas"
    / "presentation-director-plan-production-input-v1.schema.json": GovernedPlanProductionInputV1,
}


def serialized_schema(
    model: type[PresentationDirectorPlanV1] | type[GovernedPlanProductionInputV1],
) -> str:
    return (
        json.dumps(
            model.model_json_schema(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    for output, model in OUTPUTS.items():
        expected = serialized_schema(model)
        if args.check:
            if not output.is_file() or output.read_text(encoding="utf-8") != expected:
                raise SystemExit(f"schema drift: {output}")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(expected, encoding="utf-8")
        print(output)


if __name__ == "__main__":
    main()
