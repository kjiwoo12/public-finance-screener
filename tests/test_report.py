"""조서가 스스로를 속이지 않는지 확인한다.

"예쁘게 나오는가"는 보지 않는다. 넷을 본다.

  혼자 열리는가        -- 외부 참조 0, 태그 주입 이스케이프, 두 번 렌더하면 같은 바이트
  보태지 않는가        -- 렌더러가 계산하지 않고, 원문을 한 글자도 바꾸지 않는가
  감추지 않는가        -- 모집단 수가 맞고, 사라진 행이 화면에 나오는가
  근거까지 닿는가      -- 원본 CSV 값이 실제로 렌더링되고, 기본은 접혀 있는가
"""

import re
import unittest
from pathlib import Path

from report.render import CSS, _mark, render
from report.workpaper import build

ROOT = Path(__file__).resolve().parent.parent


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = build()
        cls.html = render(cls.payload)


class TestSelfContained(Base):
    def test_no_external_references(self):
        """CDN 은 보존 대상이 아니다. 5년 뒤에 열어도 같은 문서여야 한다."""
        for tag in ("<script", "<link", "<img", "<iframe", "@import"):
            self.assertNotIn(tag, self.html, f"{tag} 로 바깥을 참조한다")
        self.assertNotIn("http://", self.html.replace("http://www.w3.org", ""))
        self.assertNotIn("https://", self.html)

    def test_no_javascript(self):
        """드릴다운은 <details> 로만 만든다. 인쇄와 보존이 쉬워진다."""
        self.assertNotIn("onclick", self.html)
        self.assertNotIn("javascript:", self.html)

    def test_injected_markup_is_escaped(self):
        """기관명은 원본 문자열이다. 그대로 넣으면 문서가 깨진다."""
        p = build()
        p["procedures"][0]["findings"][0]["ent_name"] = "<script>x</script>"
        out = render(p)
        self.assertNotIn("<script>x", out)
        self.assertIn("&lt;script&gt;x", out)

    def test_rendering_twice_gives_the_same_bytes(self):
        """렌더된 조서를 커밋하므로 매번 달라지면 diff 가 뜻을 잃는다."""
        self.assertEqual(render(self.payload), render(build()))

    def test_no_wall_clock_timestamp(self):
        """실행 시각이 들어가면 위 결정론이 조용히 깨진다."""
        self.assertEqual(
            re.findall(r"\d{4}-\d{2}-\d{2}", self.html), [],
            "날짜처럼 보이는 문자열이 있다. 실행 시각이 새어 들어왔는지 확인하라")


class TestNothingIsAdded(Base):
    def test_renderer_does_not_reach_into_the_data(self):
        """렌더러가 계산하기 시작하면 화면과 코드가 갈라진다."""
        source = (ROOT / "report" / "render.py").read_text(encoding="utf-8")
        body = source.split('"""', 2)[2]  # 모듈 설명은 뺀다
        for banned in ("import screen", "from screen", "import benchmark",
                       "from benchmark", "open(", "csv"):
            self.assertNotIn(banned, body, f"렌더러가 '{banned}' 를 쓴다")

    def test_every_finding_appears_verbatim(self):
        for p in self.payload["procedures"]:
            for f in p["findings"]:
                with self.subTest(f["ent_name"]):
                    self.assertIn(f["headline"].replace("<", "&lt;"), self.html)
                    for line in f["calculation"]:
                        self.assertIn(line, self.html)
                    for q in f["open_questions"]:
                        self.assertIn(q, self.html)

    def test_rules_do_not_carry_markup(self):
        """규칙이 HTML 을 들고 있으면 출력 형식이 바뀔 때마다 규칙을 고쳐야 한다."""
        for p in self.payload["procedures"]:
            for field in ("purpose", "plain"):
                self.assertNotIn("<", p.get(field, ""), f"{field} 에 태그가 있다")

    def test_emphasis_marks_survive_escaping(self):
        """*별표* 는 강조가 되고, 본문에 든 태그는 글자로 남아야 한다."""
        self.assertEqual(_mark("가*나*다"), "가<b>나</b>다")
        self.assertEqual(_mark("<b>x</b>"), "&lt;b&gt;x&lt;/b&gt;")

    def test_thresholds_come_from_the_rule_not_the_renderer(self):
        """임계값을 렌더러가 다시 적으면 상수를 고쳐도 화면이 안 바뀐다."""
        for _, value, _ in self.payload["procedures"][0]["thresholds"]:
            self.assertNotIn(value, CSS)
            self.assertIn(value, self.html)


class TestNothingIsHidden(Base):
    def test_population_reconciles(self):
        """원본 행수부터 살펴본 수까지 중간에 사라지는 건이 없어야 한다."""
        pop = self.payload["population"]
        steps = dict((label, n) for label, n, _ in pop["steps"])
        lost = sum(len(v) for v in pop["lost"].values())
        self.assertEqual(steps["원본 CSV 행"],
                         steps["색인된 기관-연도"] + lost,
                         "원본 행수와 색인 수의 차이가 설명되지 않는다")

    def test_examined_equals_findings_plus_excluded(self):
        t = self.payload["totals"]
        self.assertEqual(t["examined"], t["findings"] + t["excluded"],
                         "살펴본 건 중 어디에도 안 잡힌 것이 있다")

    def test_dropped_rows_are_named_on_the_page(self):
        """빠진 행을 수만 적고 넘어가면 무엇이 빠졌는지 알 수 없다."""
        pop = self.payload["population"]
        if not pop["lost"]:
            self.skipTest("지금은 빠진 행이 없다")
        for reason, items in pop["lost"].items():
            self.assertIn(reason, self.html)
            for item in items:
                self.assertIn(item, self.html)
        self.assertIn("검토된 적이 없다", self.html)

    def test_empty_sections_are_explained_not_blank(self):
        """빈칸은 '검토 안 함'과 '해당 없음'을 구별해 주지 못한다."""
        p = build()
        p["procedures"][0]["excluded"] = {}
        p["procedures"][0]["findings"] = []
        out = render(p)
        self.assertIn("제외 기록이 없다", out)
        self.assertIn("발견사항이 없다", out)

    def test_a_finding_without_open_questions_is_called_out(self):
        """못 하는 것을 안 적으면 질문이 아니라 판정이 된다."""
        p = build()
        p["procedures"][0]["findings"][0]["open_questions"] = []
        self.assertIn("판정이 된다", render(p))

    def test_the_page_says_precision_was_never_measured(self):
        self.assertIn("정밀도는 애초에 잴 수 없다", self.html)
        self.assertIn("채점된 적이 없다", self.html)

    def test_excluded_comes_before_findings(self):
        """발견사항을 먼저 놓으면 읽는 사람은 거기서 멈춘다.

        칸 이름이나 번호 표기가 바뀌어도 순서만은 지켜지는지 본다.
        """
        titles = re.findall(r"<h2>.*?</i>([^<]+)</h2>", self.html)
        self.assertEqual(
            titles,
            ["모집단", "적용 절차", "제외", "발견사항",
             "이 조서가 말할 수 없는 것"],
            "조서의 칸 순서가 바뀌었다")


class TestDrilldownReachesSource(Base):
    def test_raw_rows_are_rendered(self):
        f = self.payload["procedures"][0]["findings"][0]
        self.assertTrue(f["evidence"], "발견사항에 원본 행이 없다")
        for e in f["evidence"]:
            for key, value in e["fields"].items():
                self.assertIn(key, self.html)
                self.assertIn(value, self.html)

    def test_details_are_closed_by_default(self):
        """펼쳐 두면 아무도 결론을 안 읽고, 빼 버리면 아무도 안 믿는다."""
        self.assertNotIn("<details open", self.html)
        self.assertIn("<details>", self.html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
