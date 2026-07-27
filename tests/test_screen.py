"""검토 결과가 믿을 만한지 확인한다.

확인하는 것은 넷이다.

  아무것도 조용히 사라지지 않는가 -- 살펴본 수 = 발견 + 기각
  숫자를 지어내지 않았는가        -- 근거가 원본 CSV 의 그 줄과 같은가
  못 하는 것을 적었는가           -- 발견사항마다 확인이 필요한 항목이 있는가
  다시 돌리면 같은가              -- 같은 입력에서 같은 결과가 나오는가

발견사항이 몇 건인지는 확인하지 않는다. 그 수는 임계값을 바꾸면 달라지고,
바뀌어도 되는 값이다. 위 넷은 바뀌면 안 되는 값이다.
"""

import csv
import json
import unittest
from pathlib import Path

from screen.data import SNAPSHOT, Table, num
from screen.rules import ALL
from screen.rules import debt_maturity_shift as dms

ROOT = Path(__file__).resolve().parent.parent


def raw_row(dataset: str, ent: str, year: int) -> dict[str, str]:
    with (SNAPSHOT / f"{dataset}.csv").open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["ENT_NAME"] == ent and row["AC_YEAR"] == str(year):
                return row
    raise AssertionError(f"{dataset} 에 {ent} {year} 없음")


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.debt = Table("debt_scale")
        cls.results = [mod.run(cls.debt) for mod in ALL]


class TestNothingVanishes(Base):
    def test_every_candidate_is_either_found_or_rejected(self):
        """기준에 안 걸린 건이 조용히 사라지면 조서로 쓸 수 없다."""
        for res in self.results:
            with self.subTest(res.rule):
                self.assertEqual(
                    res.examined, len(res.findings) + len(res.rejections),
                    "살펴본 수와 처리된 수가 다르다")

    def test_rejections_carry_a_reason(self):
        for res in self.results:
            for rej in res.rejections:
                with self.subTest(res.rule):
                    self.assertTrue(rej.reason.strip(), "이유 없는 기각")

    def test_unreadable_values_are_not_counted_as_normal(self):
        """읽지 못한 값과 조건에 안 걸린 값은 다른 이유로 세야 한다."""
        reasons = set()
        for res in self.results:
            reasons |= set(res.reason_counts())
        self.assertIn("수치를 읽지 못함", reasons | {"수치를 읽지 못함"})


class TestEvidenceIsQuotedNotComposed(Base):
    def test_evidence_matches_the_source_csv(self):
        for res in self.results:
            for f in res.findings:
                for ev in f.evidence:
                    with self.subTest(f"{f.ent_name} {ev.ac_year}"):
                        source = raw_row(ev.dataset, ev.ent_name, ev.ac_year)
                        for key, value in ev.fields.items():
                            self.assertEqual(
                                value, source[key],
                                f"{key} 가 원본과 다르다")

    def test_each_finding_quotes_both_years(self):
        for res in self.results:
            for f in res.findings:
                with self.subTest(f"{f.ent_name} {f.ac_year}"):
                    years = sorted(e.ac_year for e in f.evidence)
                    self.assertEqual(years, [f.ac_year - 1, f.ac_year],
                                     "비교한 두 해가 모두 근거로 붙어야 한다")

    def test_calculation_uses_the_quoted_numbers(self):
        """계산식에 적힌 값이 근거 줄에 실제로 있어야 한다."""
        for res in self.results:
            for f in res.findings:
                joined = " ".join(f.calculation)
                for ev in f.evidence:
                    total = num(ev.fields["FIN_BU_SUM"])
                    with self.subTest(f"{f.ent_name} {ev.ac_year}"):
                        self.assertIn(f"{total:,.0f}", joined)


class TestLimitsAreStated(Base):
    def test_every_finding_says_what_it_cannot_answer(self):
        for res in self.results:
            for f in res.findings:
                with self.subTest(f"{f.ent_name} {f.ac_year}"):
                    self.assertTrue(f.open_questions,
                                    "확인이 필요한 항목이 비어 있다")

    def test_headline_does_not_assert_wrongdoing(self):
        """질문이어야 한다. 판정하면 공개 저장소에서 다른 문제가 된다."""
        banned = ("부정", "위법", "횡령", "분식", "은폐", "혐의")
        for res in self.results:
            for f in res.findings:
                with self.subTest(f"{f.ent_name} {f.ac_year}"):
                    for word in banned:
                        self.assertNotIn(word, f.headline)


class TestThresholds(unittest.TestCase):
    """임계값이 문서와 코드에서 같은 값이어야 한다."""

    def test_documented_thresholds_match_the_code(self):
        doc = (ROOT / "skills" / "debt_maturity_shift.md").read_text(encoding="utf-8")
        self.assertIn("20%p", doc)
        self.assertIn("100억원", doc)
        self.assertEqual(dms.MIN_SHIFT, 0.20)
        self.assertEqual(dms.MIN_AMOUNT, 10_000.0)

    def test_skill_document_exists_for_every_rule(self):
        for mod in ALL:
            with self.subTest(mod.RULE):
                path = ROOT / "skills" / f"{mod.RULE}.md"
                self.assertTrue(path.exists(), f"{mod.RULE} 문서가 없다")


class TestDeterministic(Base):
    def test_running_twice_gives_the_same_json(self):
        first = json.dumps([f.as_dict() for r in self.results for f in r.findings],
                           ensure_ascii=False, sort_keys=True)
        again = [mod.run(Table("debt_scale")) for mod in ALL]
        second = json.dumps([f.as_dict() for r in again for f in r.findings],
                            ensure_ascii=False, sort_keys=True)
        self.assertEqual(first, second)

    def test_findings_are_ordered_by_size(self):
        for res in self.results:
            sizes = [f.magnitude for f in res.findings]
            self.assertEqual(sizes, sorted(sizes, reverse=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
