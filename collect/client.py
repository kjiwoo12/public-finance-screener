"""공공데이터포털 호출부. 표준 라이브러리만 쓴다.

원칙 하나: 받은 XML 을 그대로 먼저 저장한다.

이 저장소의 최종 산출물은 "이 기관 이 항목은 물어봐야 한다"는 질문 목록이고,
질문에는 반드시 원본이 붙어야 한다. 파싱한 값만 남기면 나중에 "그 숫자
어디서 나왔냐"에 답할 수 없다. 원본을 지우는 순간 조서가 아니라 주장이 된다.

키는 .env 에서만 읽는다. 코드에 적지 않고, 로그에도 남기지 않는다.
"""

import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from .datasets import BASE, YEARS, Dataset

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

# 개발계정 한도는 일 10,000 건이고 우리가 쓰는 건 서른 번 남짓이다. 한도가
# 아니라 상대 서버를 위해 쉬어 간다.
PAUSE = 0.4
RETRIES = 3
PAGE_SIZE = 1000


class ApiError(RuntimeError):
    pass


def load_key(env_path: Path | None = None) -> str:
    """.env 에서 키를 읽는다. 없으면 무엇을 해야 하는지 알려 주고 멈춘다."""
    path = env_path or (ROOT / ".env")
    if not path.exists():
        raise ApiError(
            f"{path} 가 없다. .env.example 을 .env 로 복사하고 "
            "data.go.kr 에서 받은 인증키를 넣어라."
        )
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == "KLID_SERVICE_KEY":
            key = value.strip().strip("'\"")
            if not key:
                raise ApiError(".env 의 KLID_SERVICE_KEY 가 비어 있다.")
            return key
    raise ApiError(".env 에 KLID_SERVICE_KEY 줄이 없다.")


def _scrub(text: str, key: str) -> str:
    """예외 메시지에 키가 섞여 나가지 않게 한다."""
    return text.replace(key, "<KEY>").replace(urllib.parse.quote(key, safe=""), "<KEY>")


def fetch_page(ds: Dataset, key: str, year: int | None, page: int) -> str:
    params = {
        "serviceKey": key,
        "type": "xml",
        "pageNo": str(page),
        "numOfRows": str(PAGE_SIZE),
    }
    # acYear 가 아니다. 서버 오류 메시지를 믿으면 영원히 같은 오류를 본다.
    # 시도코드는 연도와 무관한 코드표인데도 이 값을 요구한다. 없으면 거부하므로
    # 아무 해나 넣어 준다. 응답은 어느 해를 넣든 같다.
    params["ac_year"] = str(year if year is not None else YEARS[-1])

    url = f"{BASE}/{ds.path}?" + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return resp.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise ApiError(_scrub(f"{ds.title} {year} {page}쪽 실패: {last}", key))


def _header(doc: str) -> tuple[str, str]:
    root = ET.fromstring(doc)
    code = root.findtext(".//resultCode") or "?"
    msg = root.findtext(".//resultMsg") or "?"
    return code, msg


def _total(doc: str) -> int:
    root = ET.fromstring(doc)
    text = root.findtext(".//totalCount")
    return int(text) if text and text.isdigit() else 0


def fetch(ds: Dataset, key: str, year: int | None) -> list[str]:
    """한 데이터셋·한 해를 전부 받는다. 쪽 단위 원문을 그대로 돌려준다."""
    pages: list[str] = []
    first = fetch_page(ds, key, year, 1)
    code, msg = _header(first)
    if code != "0":
        raise ApiError(f"{ds.title} {year}: resultCode={code} {msg}")
    pages.append(first)

    total = _total(first)
    got = PAGE_SIZE
    page = 1
    while got < total:
        page += 1
        time.sleep(PAUSE)
        pages.append(fetch_page(ds, key, year, page))
        got += PAGE_SIZE
    return pages


def raw_path(ds: Dataset, year: int | None, page: int) -> Path:
    stem = f"{ds.key}_{year}" if year is not None else ds.key
    return RAW / f"{stem}_p{page}.xml"


def save(ds: Dataset, year: int | None, pages: list[str]) -> list[Path]:
    RAW.mkdir(parents=True, exist_ok=True)
    written = []
    for i, doc in enumerate(pages, start=1):
        p = raw_path(ds, year, i)
        # 줄바꿈을 고정한다. 같은 응답이 OS 에 따라 다른 파일이 되면
        # 커밋해 두고 비교하는 의미가 없다.
        p.write_text(doc, encoding="utf-8", newline="\n")
        written.append(p)
    return written
