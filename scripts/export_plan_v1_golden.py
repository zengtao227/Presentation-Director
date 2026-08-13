from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from presentation_director_contracts.plan_v1 import presentation_director_plan_v1_bytes
from presentation_director_contracts.producer_v1 import (
    GovernedPlanProductionInputV1,
    compile_presentation_director_plan_v1,
)

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_INPUT = ROOT / "fixtures" / "presentation-director-plan-production-input-v1.golden.json"
PLAN = ROOT / "fixtures" / "presentation-director-plan-v1.golden.json"
DIGEST = ROOT / "fixtures" / "presentation-director-plan-v1.golden.sha256"


def expected_artifacts() -> tuple[bytes, str]:
    payload = json.loads(PRODUCTION_INPUT.read_text(encoding="utf-8"))
    production_input = GovernedPlanProductionInputV1.model_validate(payload)
    plan = compile_presentation_director_plan_v1(production_input)
    plan_bytes = presentation_director_plan_v1_bytes(plan)
    digest = hashlib.sha256(plan_bytes).hexdigest() + "\n"
    return plan_bytes, digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    plan_bytes, digest = expected_artifacts()

    if args.check:
        if not PLAN.is_file() or PLAN.read_bytes() != plan_bytes:
            raise SystemExit(f"golden Plan drift: {PLAN}")
        if not DIGEST.is_file() or DIGEST.read_text(encoding="utf-8") != digest:
            raise SystemExit(f"golden digest drift: {DIGEST}")
    else:
        PLAN.write_bytes(plan_bytes)
        DIGEST.write_text(digest, encoding="utf-8")
    print(PLAN)
    print(DIGEST)


if __name__ == "__main__":
    main()
