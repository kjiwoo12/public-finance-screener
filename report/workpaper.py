"""검토 결과를 조서의 모양으로 옮긴다.

조서는 네 칸이다. 모집단 / 적용 절차 / 제외 / 발견사항. 감사인이 쓰던 서식이
그 순서이고, 이 도구가 내놓는 것을 그 칸에 넣을 수 없으면 받아서 쓸 수 없다.

여기서 값을 만들지 않는다. `screen/` 이 이미 만든 것을 칸에 나눠 담을 뿐이고,
한 군데만 예외다 -- **모집단 대사**. 원본 CSV 행수부터 살펴본 연도쌍까지 수가
어떻게 줄어드는지를 여기서 맞춘다. 이 대사를 하지 않으면 색인에서 사라진 행이
아무 데도 안 나타난다. 실제로 그런 행이 있었고, 조서를 만들기 전까지 아무도
몰랐다.

## 왜 작성일시를 넣지 않는가

조서에는 작성일이 들어가는 것이 보통이지만, 실행 시각을 찍으면 같은 자료에서
매번 다른 바이트가 나온다. 렌더된 조서를 저장소에 커밋해 두므로 그러면 diff 가
뜻을 잃는다. 대신 **자료의 회계연도 범위**를 적는다. 조서가 무엇을 근거로
만들어졌는지는 그쪽이 더 정확히 말해 준다.
"""

from __future__ import annotations

from typing import Any

from benchmark.grades import Grades, comparable
from screen.data import Table
from screen.rules import ALL


def _population(debt: Table, examined: int) -> dict[str, Any]:
    """원본 행수에서 살펴본 연도쌍까지, 수가 줄어드는 자리를 전부 적는다."""
    years = sorted({int(r["AC_YEAR"]) for r in debt.rows
                    if r.get("AC_YEAR", "").isdigit()})
    indexed = len(debt.rows) - len(debt.lost)
    entities = len(debt.entities())

    lost_by_reason: dict[str, list[str]] = {}
    for reason, row in debt.lost:
        lost_by_reason.setdefault(reason, []).append(
            f"{row.get('ENT_NAME', '?')} {row.get('AC_YEAR', '?')}")

    return {
        "dataset": debt.key,
        "source": f"data/snapshot/{debt.key}.csv",
        "years": years,
        "steps": [
            ("원본 CSV 행", len(debt.rows), ""),
            ("색인된 기관-연도", indexed,
             "같은 기관·같은 연도가 두 번 나오면 뒤엣것을 버린다"),
            ("기관 수", entities, f"{years[0]}~{years[-1]} 중 한 해라도 자료가 있는 곳"),
            ("살펴본 연도쌍", examined,
             "직전 연도 자료가 있어야 변화를 볼 수 있다"),
        ],
        "lost": lost_by_reason,
    }


def _procedure(mod, res, grades: Grades) -> dict[str, Any]:
    found = [(f.ent_name, f.ac_year) for f in res.findings]
    n_comparable = sum(1 for p in found if comparable(grades.status(*p)))
    n_low = sum(1 for p in found if grades.status(*p) == "하위등급 (라·마)")

    return {
        "rule": res.rule,
        "title": res.title,
        "purpose": getattr(mod, "PURPOSE", ""),
        "dataset": getattr(mod, "DATASET", ""),
        "doc": getattr(mod, "DOC", ""),
        "thresholds": list(getattr(mod, "THRESHOLDS", [])),
        "examined": res.examined,
        "excluded": res.reason_counts(),
        "findings": [f.as_dict() for f in res.findings],
        "grade_check": {"comparable": n_comparable, "low": n_low},
    }


def build() -> dict[str, Any]:
    debt = Table("debt_scale")
    grades = Grades()
    pairs = [(mod, mod.run(debt)) for mod in ALL]

    procedures = [_procedure(mod, res, grades) for mod, res in pairs]
    examined = sum(p["examined"] for p in procedures)

    return {
        "subject": "지방공기업 결산자료 이상징후 검토",
        "population": _population(debt, examined),
        "procedures": procedures,
        "totals": {
            "examined": examined,
            "findings": sum(len(p["findings"]) for p in procedures),
            "excluded": sum(sum(p["excluded"].values()) for p in procedures),
        },
    }
