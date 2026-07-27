"""스냅샷을 기관·연도로 찾아 쓸 수 있게 얹는다.

수치 변환은 여기서만 한다. 그리고 실패를 삼키지 않는다 -- 숫자로 못 읽은
값은 None 이 되고, 규칙은 None 을 만나면 판단을 포기하고 그 사실을 남긴다.
0 으로 바꿔 버리면 "없는 값"과 "0원"이 같아지고, 재정 데이터에서 이 둘은
완전히 다른 뜻이다.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "data" / "snapshot"


def num(text: str | None) -> float | None:
    """숫자로 읽는다. 못 읽으면 0 이 아니라 None 이다."""
    if text is None:
        return None
    t = text.strip().replace(",", "")
    if not t or t == "-":
        return None
    try:
        return float(t)
    except ValueError:
        return None


class Table:
    """한 데이터셋. (기관명, 연도) 로 찾는다."""

    def __init__(self, key: str):
        self.key = key
        path = SNAPSHOT / f"{key}.csv"
        with path.open(encoding="utf-8", newline="") as fh:
            self.rows: list[dict[str, str]] = list(csv.DictReader(fh))
        self._index: dict[tuple[str, int], dict[str, str]] = {}
        for row in self.rows:
            name = row.get("ENT_NAME", "")
            year = row.get("AC_YEAR", "")
            if name and year.isdigit():
                self._index[(name, int(year))] = row

    def get(self, ent_name: str, ac_year: int) -> dict[str, str] | None:
        return self._index.get((ent_name, ac_year))

    def years(self, ent_name: str) -> list[int]:
        return sorted(y for (n, y) in self._index if n == ent_name)

    def entities(self) -> list[str]:
        return sorted({n for (n, _) in self._index})

    def pairs(self) -> list[tuple[str, int]]:
        """직전 연도가 있는 (기관, 연도) 만. 변화를 보는 규칙이 쓴다."""
        out = []
        for name in self.entities():
            years = self.years(name)
            for y in years:
                if y - 1 in years:
                    out.append((name, y))
        return out
