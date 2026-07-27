"""대조가 스스로를 속이지 않는지 확인한다.

확인하는 것은 넷이다.

  연도를 맞게 붙였는가       -- '2023(2022)' 는 회계연도 2022 다
  모르는 것을 아는 척 안 하는가 -- 평가 대상이 아닌 해가 분모에 들어가면 안 된다
  이름이 실제로 이어지는가    -- 대조 대상이 몇 개나 되는지
  주장이 자료와 맞는가       -- 문서에 적은 수와 자료에서 세는 수가 같은가

대조 결과가 좋은지 나쁜지는 확인하지 않는다. 그건 자료가 정하는 것이고,
나빠도 통과해야 한다.
"""

import unittest
from pathlib import Path

from benchmark.grades import (AMBIGUOUS, MATCHED_LOW, MATCHED_MID, NOT_RATED,
                              Grades, _target_year, comparable)
from benchmark.__main__ import classify, share_low
from screen.data import Table
from screen.rules import ALL

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK = ROOT / "data" / "benchmark"


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grades = Grades()
        cls.debt = Table("debt_scale")
        cls.results = [mod.run(cls.debt) for mod in ALL]


class TestYearAlignment(unittest.TestCase):
    def test_target_year_is_the_one_in_parentheses(self):
        """괄호 밖을 쓰면 대조 전체가 한 해씩 밀린다."""
        self.assertEqual(_target_year("2023(2022)"), 2022)
        self.assertEqual(_target_year("2021(2020)"), 2020)
        self.assertIsNone(_target_year("기관명"))

    def test_columns_cover_the_years_the_screener_compares(self):
        grades = Grades()
        self.assertEqual(sorted(grades.years.values()),
                         [2020, 2021, 2022, 2023, 2024])


class TestUnknownIsNotNormal(Base):
    def test_not_rated_is_excluded_from_the_denominator(self):
        """'평가 대상이 아님'을 분모에 넣으면 '문제없음'으로 바뀐다."""
        counts = classify([("가평군상수도", 2021)], self.grades)
        self.assertEqual(counts[NOT_RATED], 1)
        low, total = share_low(counts)
        self.assertEqual((low, total), (0, 0), "대조 못 한 건이 분모에 들어갔다")

    def test_not_rated_is_not_treated_as_low(self):
        self.assertFalse(comparable(NOT_RATED))
        self.assertFalse(comparable(AMBIGUOUS))
        self.assertTrue(comparable(MATCHED_LOW))
        self.assertTrue(comparable(MATCHED_MID))

    def test_duplicated_names_are_refused(self):
        """같은 이름의 기관이 둘이면 반씩 맞다고 치지 않고 뺀다."""
        self.assertIn("고성군상수도", self.grades.duplicated)
        self.assertEqual(self.grades.status("고성군상수도", 2022), AMBIGUOUS)
        self.assertIsNone(self.grades.raw("고성군상수도", 2022))

    def test_every_examined_pair_gets_one_of_the_five_verdicts(self):
        allowed = {MATCHED_LOW, MATCHED_MID, NOT_RATED, AMBIGUOUS,
                   "대조 불가 — 등급표에 없는 기관"}
        for res in self.results:
            pairs = [(f.ent_name, f.ac_year) for f in res.findings]
            pairs += [(r.ent_name, r.ac_year) for r in res.rejections]
            for name, year in pairs:
                with self.subTest(f"{name} {year}"):
                    self.assertIn(self.grades.status(name, year), allowed)


class TestNamesActuallyJoin(Base):
    def test_almost_every_institution_is_in_the_grade_table(self):
        """이름으로 잇는 것이라 회귀하면 대조가 조용히 비어 버린다."""
        ours = set(self.debt.entities())
        matched = ours & self.grades.names()
        self.assertGreaterEqual(len(matched), 420, f"{len(matched)}개만 이어졌다")


class TestClaimsMatchTheData(Base):
    def test_bai_list_has_no_overlap_with_the_compared_years(self):
        """'감사원으로 대조할 수 있는 건은 0건'이 실제로 그런지 센다.

        발견사항의 회계연도(2021~2024)와, 감사원이 그 기관을 표제로 감사해
        공개한 연도를 견준다. 공개 연도는 감사 대상 연도보다 늦으므로,
        공개가 발견 연도보다 이르면 그 감사는 그 해를 보지 않은 것이다.
        """
        lines = (BENCHMARK / "bai_since_2020.tsv").read_text(
            encoding="utf-8").splitlines()[1:]
        titles = [(int(line.split("\t")[0][:4]), line.split("\t")[3])
                  for line in lines]

        overlapping = []
        for res in self.results:
            for f in res.findings:
                for open_year, title in titles:
                    if f.ent_name in title and open_year > f.ac_year:
                        overlapping.append((f.ent_name, f.ac_year, title))
        self.assertEqual(overlapping, [],
                         "감사원 자료로 대조 가능한 건이 생겼다. 문서를 고쳐야 한다.")

    def test_documented_numbers_match_what_the_code_counts(self):
        doc = (ROOT / "skills" / "benchmark.md").read_text(encoding="utf-8")

        found = [(f.ent_name, f.ac_year)
                 for res in self.results for f in res.findings]
        _, n_comparable = share_low(classify(found, self.grades))
        self.assertIn(f"대조된 것 {n_comparable}건", doc,
                      "문서에 적힌 대조 건수가 코드가 세는 수와 다르다")

    def test_low_grades_are_the_bottom_two(self):
        doc = (ROOT / "skills" / "benchmark.md").read_text(encoding="utf-8")
        self.assertIn("라·마", doc)
        self.assertEqual(self.grades.status("당진도시공사", 2021), MATCHED_LOW)
        self.assertEqual(self.grades.status("부산도시공사", 2021), MATCHED_MID)

    def test_precision_is_never_reported(self):
        """정밀도는 낼 수 없는 숫자다. 코드에 들어오면 문서가 거짓말이 된다."""
        source = "\n".join(
            p.read_text(encoding="utf-8")
            for p in (ROOT / "benchmark").glob("*.py"))
        for word in ("precision", "정밀도", "정확도", "적중률"):
            self.assertNotIn(word, source, f"'{word}' 를 계산하고 있다")


class TestDeterministic(Base):
    def test_reading_twice_gives_the_same_table(self):
        again = Grades()
        for name in sorted(self.grades.names())[:50]:
            for year in (2021, 2022, 2023, 2024):
                self.assertEqual(self.grades.raw(name, year),
                                 again.raw(name, year))


if __name__ == "__main__":
    unittest.main(verbosity=2)
