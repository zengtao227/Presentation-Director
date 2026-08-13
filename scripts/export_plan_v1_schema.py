from __future__ import annotations

import json
from pathlib import Path

from presentation_director_contracts.plan_v1 import PresentationDirectorPlanV1

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "schemas" / "presentation-director-plan-v1.schema.json"


def main() -> None:
    schema = PresentationDirectorPlanV1.model_json_schema()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT)


if __name__ == "__main__":
    main()
