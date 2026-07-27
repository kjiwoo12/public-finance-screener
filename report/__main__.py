"""조서를 만든다.

  python -m report                          docs/workpaper.html 로
  python -m report -o out/w.html            자리를 정해서
  python -m report --json out/w.json        조서 내용만 JSON 으로

인증키가 필요 없다. 커밋된 스냅샷만 읽는다.
"""

import argparse
import json
import sys
from pathlib import Path

from screen.data import ROOT

from .render import render
from .workpaper import build

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT = Path("docs") / "workpaper.html"


def _resolve(p: Path) -> Path:
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    ap = argparse.ArgumentParser(description="검토조서 렌더러")
    ap.add_argument("-o", "--out", type=Path, default=DEFAULT,
                    help=f"HTML 저장 위치 (기본 {DEFAULT})")
    ap.add_argument("--json", type=Path, help="조서 내용을 JSON 으로도 저장")
    args = ap.parse_args()

    payload = build()

    out = _resolve(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # 줄바꿈을 고정한다. 렌더된 조서를 커밋하므로 플랫폼마다 바이트가
    # 달라지면 diff 가 뜻을 잃는다.
    out.write_text(render(payload), encoding="utf-8", newline="\n")
    print(f"조서: {out}")

    if args.json:
        j = _resolve(args.json)
        j.parent.mkdir(parents=True, exist_ok=True)
        j.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8", newline="\n")
        print(f"내용: {j}")

    t = payload["totals"]
    print(f"  살펴본 {t['examined']:,}건 → 발견 {t['findings']}건, "
          f"제외 {t['excluded']:,}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
