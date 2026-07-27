"""받아 둔 XML 을 표 하나로 옮긴다.

여기서 값을 고치지 않는다. "0년 93개월" 같은 이상한 표기도 그대로 옮긴다.
고치는 일은 분석 단계에서 하고, 그때 무엇을 어떻게 고쳤는지 따로 남긴다.
수집 단계에서 조용히 다듬어 버리면, 나중에 원본과 대조할 수 없고 그 순간
이 저장소의 숫자는 출처 없는 숫자가 된다.

CSV 로 떨구는 이유는 커밋해 두기 위해서다. 채용담당자가 인증키를 발급받아야
돌려볼 수 있는 저장소는 아무도 돌려보지 않는다.
"""

import csv
import xml.etree.ElementTree as ET
from pathlib import Path

from .client import RAW, ROOT
from .datasets import DATASETS, Dataset

SNAPSHOT = ROOT / "data" / "snapshot"


def items(doc: str) -> list[dict[str, str]]:
    root = ET.fromstring(doc)
    out = []
    for item in root.iter("item"):
        row = {child.tag: (child.text or "").strip() for child in item}
        out.append(row)
    return out


def read_all(ds: Dataset) -> list[dict[str, str]]:
    """그 데이터셋의 원본 파일을 연도·쪽 순서대로 모두 읽는다."""
    rows: list[dict[str, str]] = []
    for path in sorted(RAW.glob(f"{ds.key}_*.xml")):
        rows.extend(items(path.read_text(encoding="utf-8")))
    return rows


def columns(rows: list[dict[str, str]]) -> list[str]:
    """처음 나온 순서를 지킨다. 정렬해 버리면 원본의 열 순서를 잃는다."""
    seen: list[str] = []
    for row in rows:
        for k in row:
            if k not in seen:
                seen.append(k)
    return seen


def write_csv(ds: Dataset, rows: list[dict[str, str]]) -> Path:
    SNAPSHOT.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT / f"{ds.key}.csv"
    cols = columns(rows)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in cols})
    return path


def build(key: str) -> tuple[Path, int, int]:
    ds = DATASETS[key]
    rows = read_all(ds)
    path = write_csv(ds, rows)
    return path, len(rows), len(columns(rows))


def check_join_names() -> dict[str, set[str]]:
    """기관명이 데이터셋마다 어긋나는지 본다.

    조인 키가 코드가 아니라 이름 문자열이므로, 이 확인을 건너뛰면 나중에
    조용히 빠지는 기관이 생긴다. 어긋난 이름을 세어 두고 사람이 판단한다.
    """
    names: dict[str, set[str]] = {}
    for key, ds in DATASETS.items():
        if not ds.by_year:
            continue
        rows = read_all(ds)
        names[key] = {r.get("ENT_NAME", "") for r in rows if r.get("ENT_NAME")}
    return names
