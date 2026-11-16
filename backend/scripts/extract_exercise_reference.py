"""Extract traceable paragraphs from the locally stored open-access review."""

import json
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/exercise-references/PMC10801605.xml"
URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC10801605/"
TITLE = "Optimizing Resistance Training Technique to Maximize Muscle Hypertrophy"


def extract() -> list[dict[str, str]]:
    root = ElementTree.parse(SOURCE).getroot()
    chunks = []
    for section in root.findall(".//body//sec"):
        title = section.find("title")
        heading = " ".join(title.itertext()).strip() if title is not None else ""
        for paragraph in section.findall("p"):
            content = " ".join("".join(paragraph.itertext()).split())
            if content:
                chunks.append({"title": TITLE, "url": URL, "section": heading, "text": content})
    return chunks


if __name__ == "__main__":
    print(json.dumps(extract(), ensure_ascii=False, indent=2))
