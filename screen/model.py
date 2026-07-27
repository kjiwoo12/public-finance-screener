"""발견사항과 기각의 모양.

기각을 값으로 다루는 것이 이 저장소의 요점 하나다. 앞선 프로젝트에서는
기준에 안 걸린 건이 조용히 사라졌고, 그래서 조서만 봐서는 "검토하지 않았음"과
"검토했으나 해당 없음"을 구별할 수 없었다. 감사에서 이 둘은 전혀 다른 일이다.

여기서는 규칙이 후보를 떨어뜨릴 때마다 왜 떨어뜨렸는지를 남긴다.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Evidence:
    """숫자 하나가 어디서 왔는지. 지어낸 값이 아니라는 걸 보이는 자리."""

    dataset: str
    ent_name: str
    ac_year: int
    fields: dict[str, str]  # 원본 표기 그대로


@dataclass
class Finding:
    rule: str
    ent_name: str
    ac_year: int
    headline: str
    # 계산식을 문장이 아니라 식으로 남긴다. 읽는 사람이 손으로 검산할 수 있어야 한다.
    calculation: list[str] = field(default_factory=list)
    # 이 관점이 답하지 못하는 것. 비워 두지 않는다.
    open_questions: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    magnitude: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "ent_name": self.ent_name,
            "ac_year": self.ac_year,
            "headline": self.headline,
            "calculation": self.calculation,
            "open_questions": self.open_questions,
            "magnitude": self.magnitude,
            "evidence": [
                {
                    "dataset": e.dataset,
                    "ent_name": e.ent_name,
                    "ac_year": e.ac_year,
                    "fields": e.fields,
                }
                for e in self.evidence
            ],
        }


@dataclass
class Rejection:
    """살펴봤으나 올리지 않은 건. 세어 두면 빈칸이 아니게 된다."""

    rule: str
    ent_name: str
    ac_year: int
    reason: str


@dataclass
class RuleResult:
    rule: str
    title: str
    examined: int  # 들여다본 후보 수
    findings: list[Finding] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)

    def reason_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self.rejections:
            counts[r.reason] = counts.get(r.reason, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))
