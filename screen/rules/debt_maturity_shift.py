"""부채가 만기만 갈아탔는가.

관점의 근거와 임계값의 출처는 skills/debt_maturity_shift.md 에 있다.
코드는 거기 적힌 것을 그대로 옮긴 것이고, 둘이 어긋나면 문서가 맞다.
"""

from ..data import Table, num
from ..model import Evidence, Finding, Rejection, RuleResult

RULE = "debt_maturity_shift"
TITLE = "부채가 만기만 갈아탔는가"

# 임계값의 출처는 이 데이터의 분포다. 1,520개 연도쌍에서 유동부채 비중
# 증가폭의 중앙값은 0.00%p, 95분위가 24.5%p 였다. 모집단이 바뀌면 다시 정한다.
MIN_SHIFT = 0.20          # 비중 증가 20%p
MIN_AMOUNT = 10_000.0     # 유동부채 증가액 100억원 (원자료 단위: 백만원)
MAX_TOTAL_DROP = 0.20     # 총부채가 이만큼 줄었으면 상환 국면으로 보고 기각

FIELDS = ("FIN_BU_YU", "FIN_BU_GU", "FIN_BU_SUM")


def _eok(million_won: float) -> str:
    """원자료는 백만원 단위다. 읽는 사람은 억 단위로 읽는다.

    단위는 추정이 아니라 확인한 값이다. 서울주택도시개발공사 2024년
    부채계가 20,023,630 이고 이는 약 20조원으로 알려진 실제 규모와 맞는다.
    """
    return f"{million_won / 100:,.0f}억원"


# 조서의 "적용 절차" 칸에 그대로 나가는 값. 임계값 상수 바로 옆에 두는 이유는,
# 떨어뜨려 놓으면 상수를 고치고 설명을 안 고치는 일이 생기기 때문이다.
DATASET = "debt_scale"
DOC = "skills/debt_maturity_shift.md"
PURPOSE = "부채 총액은 그대로인데 고정부채가 유동부채로 넘어온 해를 찾는다."
THRESHOLDS = [
    ("유동부채 비중 증가", f"{MIN_SHIFT * 100:.0f}%p 이상",
     "이 데이터 연도쌍에서 증가폭 중앙값 0.00%p, 95분위 24.5%p"),
    ("유동부채 증가액", f"{MIN_AMOUNT / 100:,.0f}억원 이상",
     "비중만 보면 부채가 작은 기관에서 쉽게 튄다"),
    ("총부채 감소", f"{MAX_TOTAL_DROP * 100:.0f}% 이상이면 기각",
     "상환 국면이면 잔액이 전부 1년 내 만기가 되는 것이 당연하다"),
]


def _total_move(before: float, after: float) -> str:
    """총부채가 어떻게 움직였는지. 이 관점의 핵심은 총액이 아니라 만기다."""
    diff = after - before
    if abs(diff) < before * 0.05:
        return f"{_eok(before)}에서 거의 그대로였다"
    verb = "늘었다" if diff > 0 else "줄었다"
    return f"{_eok(before)}에서 {_eok(after)}으로 {verb}"


def _evidence(row: dict[str, str], year: int) -> Evidence:
    return Evidence(
        dataset="debt_scale",
        ent_name=row["ENT_NAME"],
        ac_year=year,
        fields={k: row.get(k, "") for k in ("AC_YEAR", "ENT_NAME", *FIELDS)},
    )


def run(debt: Table) -> RuleResult:
    result = RuleResult(rule=RULE, title=TITLE, examined=0)

    for name, year in debt.pairs():
        prev, curr = debt.get(name, year - 1), debt.get(name, year)
        if prev is None or curr is None:
            continue
        result.examined += 1

        def reject(reason: str) -> None:
            result.rejections.append(Rejection(RULE, name, year, reason))

        s0, s1 = num(prev["FIN_BU_SUM"]), num(curr["FIN_BU_SUM"])
        y0, y1 = num(prev["FIN_BU_YU"]), num(curr["FIN_BU_YU"])

        if None in (s0, s1, y0, y1):
            # 값을 못 읽은 것과 조건에 안 걸린 것은 다르다. 따로 센다.
            reject("수치를 읽지 못함")
            continue
        if s0 <= 0:
            reject("직전연도 부채가 0")
            continue
        if s1 <= 0:
            reject("당해연도 부채가 0")
            continue

        p0, p1 = y0 / s0, y1 / s1
        shift = p1 - p0
        amount = y1 - y0

        if shift < MIN_SHIFT:
            reject("비중 증가가 20%p 미만")
            continue
        if amount < MIN_AMOUNT:
            reject("유동부채 증가액이 100억원 미만")
            continue
        if s1 < s0 * (1 - MAX_TOTAL_DROP):
            reject("총부채가 20% 이상 감소 (상환 국면)")
            continue

        result.findings.append(Finding(
            rule=RULE,
            ent_name=name,
            ac_year=year,
            headline=(
                f"{name}: 1년 안에 갚아야 할 부채가 {year}년에 "
                f"{_eok(amount)} 늘었다. "
                f"전체 부채에서 차지하는 비중은 {p0 * 100:.1f}%에서 "
                f"{p1 * 100:.1f}%로 올랐고, "
                f"총부채는 {_total_move(s0, s1)}."
            ),
            calculation=[
                f"{year - 1}년 유동부채 비중 = {y0:,.0f} / {s0:,.0f} = {p0 * 100:.1f}%",
                f"{year}년 유동부채 비중 = {y1:,.0f} / {s1:,.0f} = {p1 * 100:.1f}%",
                f"비중 증가 = {p1 * 100:.1f}% - {p0 * 100:.1f}% = {shift * 100:.1f}%p",
                f"유동부채 증가액 = {y1:,.0f} - {y0:,.0f} = {amount:,.0f}"
                f" (백만원) = {_eok(amount)}",
            ],
            open_questions=[
                "만기가 도래한 것인가, 차환에 실패한 것인가. "
                "공시에 만기 구조가 없어 이 데이터로는 구별할 수 없다.",
                "이 기관의 사업 성격상 단기 차입을 굴리는 것이 통상적인가.",
                "해당 연도에 계정 재분류나 회계기준 변경이 있었는가.",
            ],
            evidence=[_evidence(prev, year - 1), _evidence(curr, year)],
            magnitude=amount,
        ))

    result.findings.sort(key=lambda f: -f.magnitude)
    return result
