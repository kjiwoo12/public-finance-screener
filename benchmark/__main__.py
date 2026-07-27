"""스크리너가 올린 것을 바깥 판단과 맞춰 본다.

  python -m benchmark

인증키가 필요 없다. 커밋된 스냅샷과 대조 자료만 읽는다.
"""

import sys
from collections import Counter
from pathlib import Path

from screen.data import Table
from screen.rules import ALL

from .grades import (AMBIGUOUS, MATCHED_LOW, MATCHED_MID, NO_NAME, NOT_RATED,
                     Grades, comparable)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BENCHMARK = Path(__file__).resolve().parent.parent / "data" / "benchmark"

ORDER = (MATCHED_LOW, MATCHED_MID, NOT_RATED, NO_NAME, AMBIGUOUS)


def classify(pairs, grades: Grades) -> Counter:
    return Counter(grades.status(name, year) for name, year in pairs)


def share_low(counts: Counter) -> tuple[int, int]:
    """(하위등급 수, 대조된 수). 대조 못 한 건은 분모에서도 뺀다.

    분모에 넣으면 '대조하지 못했다'가 '문제없다'로 조용히 바뀐다.
    """
    return counts[MATCHED_LOW], counts[MATCHED_LOW] + counts[MATCHED_MID]


def pct(n: int, d: int) -> str:
    return f"{n / d * 100:.1f}%" if d else "—"


def table(counts: Counter, total: int) -> None:
    for key in ORDER:
        if counts[key]:
            print(f"    {counts[key]:5}건  {key}")
    print(f"    {'-' * 5}")
    print(f"    {total:5}건  합계")


def report_rule(res, grades: Grades) -> None:
    found = [(f.ent_name, f.ac_year) for f in res.findings]
    everything = found + [(r.ent_name, r.ac_year) for r in res.rejections]

    print("=" * 72)
    print(f"[{res.rule}] {res.title}")

    print(f"\n  발견사항 {len(found)}건을 경영평가 등급과 맞춰 본다")
    fc = classify(found, grades)
    table(fc, len(found))

    print(f"\n  같은 규칙이 살펴본 {len(everything)}건 전체")
    ac = classify(everything, grades)
    table(ac, len(everything))

    f_low, f_cmp = share_low(fc)
    a_low, a_cmp = share_low(ac)

    print("\n  하위등급 비율")
    print(f"    발견사항  {f_low:4} / {f_cmp:<5} = {pct(f_low, f_cmp)}")
    print(f"    전체      {a_low:4} / {a_cmp:<5} = {pct(a_low, a_cmp)}")

    # 여기서 결론을 자동으로 내지 않는다. 대조된 건수가 두 자리도 안 되는데
    # 코드가 "유의하다/아니다"를 찍으면 그 문장이 혼자 걸어 나간다.
    print(f"\n  이 비교의 분모는 {f_cmp}건이다.", end=" ")
    if f_cmp < 30:
        print("이 수로는 두 비율의 차이를 말할 수 없다.")
    else:
        print("차이의 해석은 skills/benchmark.md 를 함께 읽어야 한다.")

    # 반대 방향. 이쪽이 실제로 셀 수 있는 것이다.
    low_pairs = {p for p in everything if grades.status(*p) == MATCHED_LOW}
    hit = len(low_pairs & set(found))
    print(f"\n  반대로 보면 — 살펴본 것 중 경영평가 하위등급은 {len(low_pairs)}건이고,")
    print(f"  그중 이 관점이 올린 것은 {hit}건이다 ({pct(hit, len(low_pairs))}).")
    print("  나머지를 '놓쳤다'고는 부를 수 없다. 하위등급의 사유가")
    print("  부채 만기와 무관한 경우가 대부분이기 때문이다.")
    print()


# 감사 보고서의 표제와 재무 데이터의 기관명이 다른 경우. 이름이 바뀌었거나
# 통칭으로 부른 것이다. 조용히 맞춰 버리면 나중에 왜 이 건이 잡혔는지 아무도
# 모르게 되므로, 여기 적어 두고 화면에도 알린다.
ALIASES = {
    "서울주택도시개발공사": "서울주택도시공사",   # 감사 시점의 이름 (SH공사)
}


def report_bai(examined_names: set[str], found_names: set[str]) -> None:
    """감사원 쪽은 세어 볼 것도 없다는 사실을 세어서 보인다."""
    lines = (BENCHMARK / "bai_since_2020.tsv").read_text(
        encoding="utf-8").splitlines()[1:]

    def keys(name: str) -> list[str]:
        return [name, ALIASES[name]] if name in ALIASES else [name]

    named = []
    for line in lines:
        date, _srno, kind, title = line.split("\t")
        for name in sorted(examined_names):
            # 표제에 우리 기관 이름이 그대로 들어간 것만 센다. 지자체 정기감사
            # 보고서 본문에 산하 공기업 지적이 들어 있는 경우는 이 방법으로
            # 잡히지 않는다 -- 그 한계는 data/benchmark/SOURCE.md 에 적었다.
            if any(k in title for k in keys(name)):
                named.append((date, kind, title, name))
                break

    print("=" * 72)
    print("[감사원] 감사결과와 맞춰 본다")
    print(f"\n  2020년 이후 공개된 감사결과 중 우리 기관을 표제로 내건 것: {len(named)}건")
    for date, kind, title, name in sorted(named):
        mark = " *" if name in found_names else "  "
        print(f"   {mark} {date[:4]}-{date[4:6]}  {kind:6}  {title}")
    if any(n in found_names for *_, n in named):
        print("\n    * 표시는 이 관점이 발견사항으로 올린 기관이다.")
    for name in sorted({n for *_, n in named} & found_names):
        if name in ALIASES:
            print(f"      ({name} 는 감사 당시 '{ALIASES[name]}' 였다)")

    print("\n  우리가 비교하는 회계연도는 2021~2024 다.")
    print("  위 감사들은 대부분 2020~2021년에 공개되었고, 대상 회계연도는")
    print("  그보다 앞선다. 같은 기관이 겹치더라도 같은 해가 아니므로,")
    print("  감사원 자료로 맞고 틀림을 말할 수 있는 발견사항은 0건이다.")
    print()


def main() -> int:
    debt = Table("debt_scale")
    grades = Grades()
    results = [mod.run(debt) for mod in ALL]

    for res in results:
        report_rule(res, grades)

    found = {f.ent_name for r in results for f in r.findings}
    examined = found | {j.ent_name for r in results for j in r.rejections}
    report_bai(examined, found)

    print("=" * 72)
    print("이 대조가 말하지 못하는 것은 skills/benchmark.md 에 적었다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
