"""지방공기업 경영평가 등급표.

이 표는 정답지가 아니다. 우리가 묻는 것(부채 만기가 갈아탔는가)과 이 표가
답하는 것(그 해 경영이 전반적으로 어땠는가)은 다른 질문이다. 그런데도 이걸
쓰는 이유는, 우리 데이터 기간에 이 기관들을 사람이 들여다보고 남긴 판단이
공개된 것 중 이것뿐이기 때문이다.

그래서 여기서 하는 일은 채점이 아니라 대조다. 일치하면 "같은 해를 다르게
보지는 않았다" 정도이고, 불일치는 틀렸다는 뜻이 아니다.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK = ROOT / "data" / "benchmark"

# 하위 두 등급. 행정안전부가 그 해 이 기관의 경영을 나쁘게 봤다는 뜻이다.
LOW = ("라", "마")

# 대조 결과는 다섯 가지뿐이다. 이 다섯 중 어디에도 안 들어가는 건이 생기면
# 그건 코드가 잘못된 것이므로 KeyError 로 터지게 둔다.
MATCHED_LOW = "하위등급 (라·마)"
MATCHED_MID = "중·상위등급 (가·나·다)"
NOT_RATED = "대조 불가 — 그 해 평가 대상이 아님"
NO_NAME = "대조 불가 — 등급표에 없는 기관"
AMBIGUOUS = "대조 불가 — 같은 이름의 기관이 둘"


def _target_year(header: str) -> int | None:
    """'2023(2022)' -> 2022.

    괄호 밖은 평가를 시행한 해, 괄호 안이 평가 대상 회계연도다. 우리
    AC_YEAR 와 맞춰야 하는 것은 괄호 안이고, 밖을 쓰면 한 해가 통째로
    밀린 채로 대조하게 된다.
    """
    m = re.search(r"\((\d{4})\)", header)
    return int(m.group(1)) if m else None


class Grades:
    def __init__(self, path: Path | None = None):
        path = path or BENCHMARK / "mng_grade.tsv"
        lines = path.read_text(encoding="utf-8").splitlines()
        header = lines[0].split("\t")

        # 열 번호 -> 회계연도
        self.years: dict[int, int] = {}
        for i, col in enumerate(header):
            year = _target_year(col)
            if year is not None:
                self.years[i] = year

        self._by_name: dict[str, dict[int, str]] = {}
        self.duplicated: set[str] = set()
        for line in lines[1:]:
            cells = line.split("\t")
            name = cells[1]
            if name in self._by_name:
                # 원본에 같은 이름이 두 번 나온다. 강원 고성군과 경남 고성군의
                # 상수도가 둘 다 '고성군상수도'다. 어느 쪽인지 알 수 없으므로
                # 둘 다 대조 대상에서 뺀다. 반씩 맞다고 치는 것보다 낫다.
                self.duplicated.add(name)
                continue
            self._by_name[name] = {
                year: cells[i] for i, year in self.years.items() if i < len(cells)
            }

    def names(self) -> set[str]:
        return set(self._by_name) - self.duplicated

    def raw(self, ent_name: str, ac_year: int) -> str | None:
        """등급표에 적힌 그대로. 없으면 None."""
        if ent_name in self.duplicated:
            return None
        return self._by_name.get(ent_name, {}).get(ac_year)

    def status(self, ent_name: str, ac_year: int) -> str:
        """이 (기관, 연도) 를 대조할 수 있는가, 있다면 어느 쪽인가."""
        if ent_name in self.duplicated:
            return AMBIGUOUS
        row = self._by_name.get(ent_name)
        if row is None:
            return NO_NAME
        grade = row.get(ac_year)
        if grade is None or grade in ("대상아님", "기타", ""):
            return NOT_RATED
        return MATCHED_LOW if grade in LOW else MATCHED_MID


def comparable(status: str) -> bool:
    return status in (MATCHED_LOW, MATCHED_MID)
