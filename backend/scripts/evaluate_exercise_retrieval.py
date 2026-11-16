"""Small reproducible smoke evaluation for a locally built semantic index."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.modules.training.exercise_retrieval import exercise_query, retrieve  # noqa: E402

CASES = (
    ("Como fazer agachamento búlgaro?", ("split squat", "dumbbell")),
    ("Como fazer agachamento?", ("bodyweight", "squat")),
    ("Como fazer supino?", ("barbell", "bench", "press")),
    ("Como executar agachamento com barra?", ("barbell", "squat")),
    ("Como realizar supino com barra?", ("barbell", "bench", "press")),
    ("Como fazer levantamento terra?", ("deadlift",)),
    ("Como fazer rosca direta?", ("barbell", "curl")),
    ("Como executar leg press?", ("leg", "press")),
    ("Como faço elevação lateral?", ("lateral", "raise")),
    ("Como fazer afundo?", ("lunge",)),
    ("Como fazer flexão?", ("push",)),
    ("Como fazer prancha?", ("plank",)),
    ("Como fazer o exercício flumbarox?", ()),
)


def main() -> int:
    failed = 0
    for question, terms in CASES:
        query = exercise_query(question)
        results = retrieve(query) if query else []
        passed = (
            any(all(term in result["section"].casefold() for term in terms) for result in results)
            if terms
            else not results
        )
        failed += not passed
        print(f"{'PASS' if passed else 'FAIL'} {question}")
    print(f"Passed {len(CASES) - failed}/{len(CASES)}")
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
