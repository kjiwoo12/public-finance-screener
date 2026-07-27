"""수집 결과가 믿을 만한지 확인한다.

확인하는 것은 넷이다.

  옮기다 흘리지 않았는가 -- 원본 XML 의 건수와 표의 행수가 같은가
  이을 수 있는가         -- 기관명이 데이터셋 사이에서 실제로 맞물리는가
  다시 만들면 같은가     -- 같은 원본에서 같은 바이트가 나오는가
  새지 않는가            -- 커밋될 파일에 인증키가 섞이지 않았는가

"보기 좋은가"는 확인하지 않는다. 여기서 틀리면 뒤에 무엇을 쌓아도 소용없다.
"""

import csv
import re
import unittest
from pathlib import Path

from collect.client import RAW
from collect.datasets import DATASETS, YEARS
from collect.normalize import SNAPSHOT, columns, read_all, write_csv

ROOT = Path(__file__).resolve().parent.parent


def load(key: str) -> list[dict[str, str]]:
    """스냅샷 한 개를 읽는다. 파일을 열어 두고 넘기면 경고가 쌓인다."""
    with (SNAPSHOT / f"{key}.csv").open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


class TestSnapshotExists(unittest.TestCase):
    def test_every_dataset_has_a_snapshot(self):
        for key, ds in DATASETS.items():
            with self.subTest(ds.title):
                path = SNAPSHOT / f"{key}.csv"
                self.assertTrue(path.exists(), f"{ds.title} 스냅샷이 없다")
                self.assertGreater(path.stat().st_size, 0)

    def test_year_based_sets_cover_every_year(self):
        for key, ds in DATASETS.items():
            if not ds.by_year:
                continue
            with self.subTest(ds.title):
                rows = load(key)
                years = {int(r["AC_YEAR"]) for r in rows if r.get("AC_YEAR")}
                self.assertEqual(years, set(YEARS), f"{ds.title} 연도 누락")


class TestNothingLostInTransit(unittest.TestCase):
    def test_row_count_matches_the_raw_xml(self):
        """표의 행수는 원본 <item> 개수와 정확히 같아야 한다."""
        for key, ds in DATASETS.items():
            with self.subTest(ds.title):
                raw_items = sum(
                    p.read_text(encoding="utf-8").count("<item>")
                    for p in RAW.glob(f"{key}_*.xml")
                )
                rows = load(key)
                self.assertEqual(len(rows), raw_items, f"{ds.title} 행수 불일치")

    def test_join_keys_are_present_on_every_row(self):
        for key, ds in DATASETS.items():
            if not ds.by_year:
                continue
            with self.subTest(ds.title):
                rows = load(key)
                blank = [r for r in rows if not r.get("ENT_NAME") or not r.get("AC_YEAR")]
                self.assertEqual(blank, [], f"{ds.title} 조인 키가 빈 행 {len(blank)}개")


class TestJoinActuallyWorks(unittest.TestCase):
    """조인 키가 코드가 아니라 기관명 문자열이라, 맞물리는지 확인해야 한다."""

    @staticmethod
    def names(key: str) -> set[str]:
        return {r["ENT_NAME"] for r in load(key) if r.get("ENT_NAME")}

    def test_financial_sets_share_the_same_institutions(self):
        base = self.names("budget")
        for key in ("debt_scale", "fina_debt", "mng_idx"):
            with self.subTest(DATASETS[key].title):
                self.assertEqual(
                    self.names(key) - base, set(),
                    f"{DATASETS[key].title} 에만 있는 기관명이 있다")

    def test_wage_is_a_subset_not_a_separate_universe(self):
        """임금 데이터는 기관 수가 적다. 적은 것과 어긋난 것은 다르다."""
        extra = self.names("wage") - self.names("budget")
        self.assertEqual(extra, set(), f"임금에만 있는 기관명: {sorted(extra)[:5]}")


class TestDeterministic(unittest.TestCase):
    def test_rebuilding_gives_the_same_bytes(self):
        """같은 원본에서 다른 파일이 나오면 커밋해 두고 비교할 수 없다."""
        for key, ds in DATASETS.items():
            with self.subTest(ds.title):
                before = (SNAPSHOT / f"{key}.csv").read_bytes()
                write_csv(ds, read_all(ds))
                self.assertEqual((SNAPSHOT / f"{key}.csv").read_bytes(), before)

    def test_column_order_follows_the_source(self):
        rows = read_all(DATASETS["fina_debt"])
        self.assertEqual(columns(rows)[:3], ["No", "AC_YEAR", "ENT_NAME"])


class TestNoSecretsCommitted(unittest.TestCase):
    """인증키가 커밋될 파일에 섞이면 되돌릴 수 없다. 지우도 기록에 남는다."""

    HEXKEY = re.compile(r"\b[0-9a-fA-F]{32,}\b")

    def test_env_is_ignored(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".env", [ln.strip() for ln in ignore])

    def test_no_long_hex_in_tracked_sources(self):
        for path in list(ROOT.glob("collect/*.py")) + list(ROOT.glob("tests/*.py")):
            with self.subTest(path.name):
                hits = self.HEXKEY.findall(path.read_text(encoding="utf-8"))
                self.assertEqual(hits, [], f"{path.name} 에 키처럼 보이는 문자열")

    def test_no_long_hex_in_snapshots(self):
        for path in SNAPSHOT.glob("*.csv"):
            with self.subTest(path.name):
                hits = self.HEXKEY.findall(path.read_text(encoding="utf-8"))
                self.assertEqual(hits, [], f"{path.name} 에 키처럼 보이는 문자열")


if __name__ == "__main__":
    unittest.main(verbosity=2)
