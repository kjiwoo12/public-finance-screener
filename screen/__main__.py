"""검토를 돌리고 결과를 남긴다.

  python -m screen              화면에 요약
  python -m screen --json out/findings.json

인증키가 필요 없다. 커밋된 스냅샷만 읽는다.
"""

import argparse
import json
import sys
from pathlib import Path

from .data import ROOT, Table
from .rules import ALL

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def run_all() -> list:
    debt = Table("debt_scale")
    return [mod.run(debt) for mod in ALL]


def show(results: list) -> None:
    for res in results:
        print("=" * 72)
        print(f"[{res.rule}] {res.title}")
        print(f"  살펴본 연도쌍 {res.examined}건 "
              f"-> 발견사항 {len(res.findings)}건, 기각 {len(res.rejections)}건")

        # 기각을 이유별로 낸다. 이 표가 있어야 "검토하지 않았음"과
        # "검토했으나 해당 없음"이 구별된다.
        print("\n  기각 내역")
        for reason, n in res.reason_counts().items():
            print(f"    {n:5}건  {reason}")

        print(f"\n  발견사항 {len(res.findings)}건")
        for i, f in enumerate(res.findings, 1):
            print(f"\n  {i}. {f.ent_name} ({f.ac_year})")
            print(f"     {f.headline}")
            for line in f.calculation:
                print(f"       {line}")
            print("     확인이 필요한 것:")
            for q in f.open_questions:
                print(f"       - {q}")
        print()


def main() -> int:
    ap = argparse.ArgumentParser(description="지방공기업 재정 스크리너")
    ap.add_argument("--json", type=Path, help="발견사항을 JSON 으로 저장")
    args = ap.parse_args()

    results = run_all()
    show(results)

    if args.json:
        path = args.json if args.json.is_absolute() else ROOT / args.json
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "rule": r.rule,
                "title": r.title,
                "examined": r.examined,
                "findings": [f.as_dict() for f in r.findings],
                "rejections": r.reason_counts(),
            }
            for r in results
        ]
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n",
        )
        print(f"저장: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
