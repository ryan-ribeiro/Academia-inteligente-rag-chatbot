"""Smoke-test the semantic translation check against a few contrasting pairs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.modules.training.exercise_retrieval import evidence_matches  # noqa: E402

CASES = (
    (
        "Stand with feet shoulder-width apart.",
        "Fique em pé com os pés afastados na largura dos ombros.",
        True,
    ),
    ("Stand with feet shoulder-width apart.", "Aumente a carga em todos os exercícios.", False),
    (
        "Bend your knees and hips to lower your body.",
        "Flexione os joelhos e os quadris para abaixar o corpo.",
        True,
    ),
    (
        "Bend your knees and hips to lower your body.",
        "Estenda os joelhos e os quadris para levantar o corpo.",
        False,
    ),
    (
        "Keep your back straight during the movement.",
        "Mantenha as costas retas durante o movimento.",
        True,
    ),
    (
        "Keep your back straight during the movement.",
        "Arredonde as costas durante o movimento.",
        False,
    ),
)


def main() -> int:
    failed = 0
    for source, translation, expected in CASES:
        actual = evidence_matches([(source, translation)], threshold=0.75)
        passed = actual == expected
        failed += not passed
        print(f"{'PASS' if passed else 'FAIL'} {source} -> {translation}")
    print(f"Passed {len(CASES) - failed}/{len(CASES)}; similarity does not prove equivalence")
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
