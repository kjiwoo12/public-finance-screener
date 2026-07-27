"""수집 실행부.

  python -m collect              여섯 데이터셋을 다섯 해치 받아 CSV 까지 만든다
  python -m collect --check      받아 둔 것만 확인한다 (호출 없음, 키 불필요)
"""

import argparse
import sys

from .client import ApiError, fetch, load_key, save
from .datasets import DATASETS, YEARS
from .normalize import build, check_join_names

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def collect(years: tuple[int, ...]) -> int:
    key = load_key()
    calls = 0
    for ds in DATASETS.values():
        targets = list(years) if ds.by_year else [None]
        for year in targets:
            try:
                pages = fetch(ds, key, year)
            except ApiError as exc:
                print(f"  [x] {ds.title} {year or ''}: {exc}")
                continue
            paths = save(ds, year, pages)
            rows = sum(p.read_text(encoding="utf-8").count("<item>") for p in paths)
            calls += len(pages)
            print(f"  [o] {ds.title:9} {year or '   -'}  {rows:5}건  {len(paths)}쪽")
    return calls


def report() -> None:
    print("\n--- 표로 옮긴 결과 ---")
    for key, ds in DATASETS.items():
        try:
            path, rows, cols = build(key)
        except FileNotFoundError:
            print(f"  {ds.title}: 원본 없음")
            continue
        print(f"  {ds.title:9} {rows:5}행 {cols:3}열  {path.name}")

    print("\n--- 기관명 대조 (조인 키가 코드가 아니라 이름이므로) ---")
    names = check_join_names()
    if not names:
        return
    base_key = max(names, key=lambda k: len(names[k]))
    base = names[base_key]
    print(f"  기준: {DATASETS[base_key].title} {len(base)}개 기관명")
    for key, got in names.items():
        if key == base_key:
            continue
        missing = got - base
        mark = "" if not missing else f"  <- 기준에 없는 이름 {len(missing)}개"
        print(f"  {DATASETS[key].title:9} {len(got):4}개{mark}")
        for name in sorted(missing)[:5]:
            print(f"      {name}")


def main() -> int:
    ap = argparse.ArgumentParser(description="지방공기업 경영정보를 받아 표로 만든다")
    ap.add_argument("--check", action="store_true", help="호출 없이 받아 둔 것만 확인")
    ap.add_argument("--year", type=int, action="append", help="특정 연도만 (여러 번 가능)")
    args = ap.parse_args()

    if not args.check:
        years = tuple(args.year) if args.year else YEARS
        print(f"수집: {len(DATASETS)}개 데이터셋 × {len(years)}개 연도")
        try:
            calls = collect(years)
        except ApiError as exc:
            print(f"멈춤: {exc}")
            return 1
        print(f"\n호출 {calls}회")

    report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
