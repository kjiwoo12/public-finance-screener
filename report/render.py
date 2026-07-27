"""조서 payload → 단일 HTML 파일.

## 렌더러는 계산도 판단도 하지 않는다

내용은 `screen/` 이 만들고 `workpaper.py` 가 칸에 담는다. 여기서는 **읽는
순서만** 정한다. 렌더러가 요약하거나 보태기 시작하면 화면에 보이는 것과
코드가 계산한 것이 갈라지고, 그때부터 "이렇게 검토했다"는 말에 근거가 없다.
그래서 이 모듈은 `screen` 을 import 하지 않는다 -- 테스트가 확인한다.

## 칸의 순서

감사조서의 순서를 따른다. 다만 한 군데를 바꿨다.

    1  모집단      무엇을 다 봤다고 말하는가
    2  적용 절차   어떤 눈으로 봤는가, 임계값은 어디서 왔는가
    3  제외        올리지 않은 것과 그 이유
    4  발견사항    올린 것

**제외가 발견사항보다 앞이다.** 발견사항을 먼저 놓으면 읽는 사람은 거기서
멈추고, 조서에서 정작 방어해야 하는 것은 "그럼 저기는 왜 안 봤나" 쪽이다.
올린 16건보다 안 올린 1,604건이 이 도구가 하는 일에 가깝다.

## 감추지 않는다

빈칸은 "검토하지 않았음"과 "검토했으나 해당 없음"을 구별해 주지 못한다. 그래서
비어 있는 항목은 공백으로 두지 않고 그 사실을 문장으로 적는다.

의존성 없음. 자바스크립트도 쓰지 않는다 -- 드릴다운은 `<details>` 로만
만든다. 외부 스크립트·스타일·폰트를 하나도 참조하지 않으므로 첨부해서 보내도,
5년 뒤에 열어도 같은 문서다. 조서는 보존 대상이고 CDN 은 보존 대상이 아니다.

출력은 결정론적이다. 같은 payload 를 넣으면 항상 같은 바이트가 나온다.
"""

from __future__ import annotations

import html
from typing import Any

CSS = """
:root { --ink:#1a1a1a; --dim:#666; --line:#d8d4cc; --bg:#faf9f7;
        --box:#fff; --warn:#8a5a00; --warnbg:#fdf6e6; }
* { box-sizing:border-box; }
body { margin:0; padding:0 1.25rem 5rem; background:var(--bg); color:var(--ink);
       font:15px/1.75 "Malgun Gothic","맑은 고딕",-apple-system,sans-serif; }
main { max-width:52rem; margin:0 auto; }
h1 { font-size:1.6rem; margin:0 0 .4rem; letter-spacing:-.02em; }
h2 { font-size:1.15rem; margin:3.5rem 0 .25rem; padding-bottom:.5rem;
     border-bottom:2px solid var(--ink); }
h3 { font-size:1rem; margin:2rem 0 .5rem; }
p, li { margin:.6rem 0; }
small, .dim { color:var(--dim); }
code { font-family:Consolas,"D2Coding",monospace; font-size:.9em; }
a { color:inherit; }

header { padding:3rem 0 1.5rem; border-bottom:1px solid var(--line); }
.meta { display:grid; grid-template-columns:max-content 1fr; gap:.15rem 1.25rem;
        margin-top:1.25rem; font-size:.88rem; }
.meta dt { color:var(--dim); }
.meta dd { margin:0; }

table { border-collapse:collapse; width:100%; margin:1rem 0; font-size:.9rem; }
th, td { text-align:left; padding:.5rem .7rem; border-bottom:1px solid var(--line);
         vertical-align:top; }
th { font-weight:600; color:var(--dim); font-size:.82rem; white-space:nowrap; }
td.n { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
.wrap { overflow-x:auto; }

.note { background:var(--warnbg); border-left:3px solid var(--warn);
        padding:.85rem 1.1rem; margin:1.25rem 0; font-size:.9rem; color:var(--warn); }
.note strong { color:var(--warn); }

.bar { background:var(--line); height:.4rem; border-radius:2px; margin-top:.3rem; }
.bar > span { display:block; height:100%; background:var(--dim); border-radius:2px; }

.card { background:var(--box); border:1px solid var(--line); border-radius:4px;
        padding:1.25rem 1.4rem; margin:1.25rem 0; }
.card > h3 { margin-top:0; }
.calc { background:var(--bg); border-radius:3px; padding:.8rem 1rem; margin:.8rem 0;
        font-family:Consolas,"D2Coding",monospace; font-size:.84rem; line-height:1.9;
        white-space:pre-wrap; overflow-x:auto; }
.ask { margin:.8rem 0 0; padding-left:1.1rem; }
.ask li { margin:.35rem 0; }

details { margin-top:1rem; border-top:1px solid var(--line); padding-top:.8rem; }
summary { cursor:pointer; font-size:.85rem; color:var(--dim); }
details table { font-size:.8rem; }

@media print {
  body { background:#fff; font-size:10.5pt; padding:0; }
  .card, .note { border:1px solid #bbb; background:#fff; break-inside:avoid; }
  h2 { break-after:avoid; }
  details { border-top:1px solid #bbb; }
  details[open] summary, summary { list-style:none; }
  a { text-decoration:none; }
}
"""

# 조서가 스스로 밝혀야 하는 한계. 화면에 안 적으면 조서를 받은 사람은
# 이 도구가 맞는지 확인된 줄로 읽는다.
LIMITS = [
    ("올린 것이 맞는지 채점된 적이 없다",
     "감사원 감사결과 중 이 기관들을 표제로 다룬 것은 2020년 이후 7건이고, "
     "그 회계연도가 여기 검토한 연도와 겹치지 않는다. 채점표를 만들 자료가 없다."),
    ("정밀도는 애초에 잴 수 없다",
     "올린 건에 감사 기록이 없을 때 '문제가 없었다'와 '아무도 안 들여다봤다'는 "
     "공개 자료로 구별되지 않는다. 그래서 이 조서는 적중률을 숫자로 내지 않는다."),
    ("이 도구는 판정하지 않는다",
     "발견사항은 확인이 필요한 항목이지 지적사항이 아니다. 각 건의 '확인이 "
     "필요한 것'은 이 데이터로 답할 수 없어 사람에게 넘기는 질문이다."),
]


def _e(v: Any) -> str:
    """HTML 이스케이프. 기관명과 원본 값이 그대로 들어가므로 전부 통과시킨다."""
    return html.escape("" if v is None else str(v), quote=True)


def _rows(pairs: list[tuple[str, Any]]) -> str:
    return "".join(f"<tr><th>{_e(k)}</th><td>{_e(v)}</td></tr>" for k, v in pairs)


def _population(pop: dict) -> str:
    steps = "".join(
        f"<tr><td>{_e(label)}</td><td class='n'>{n:,}</td>"
        f"<td class='dim'>{_e(why)}</td></tr>"
        for label, n, why in pop["steps"])

    out = [
        "<h2>1. 모집단</h2>",
        "<p>원본 파일에서 살펴본 연도쌍까지 수가 어떻게 줄어드는지 적는다. "
        "중간에 사라진 행이 있으면 여기서 드러난다.</p>",
        f"<div class='wrap'><table><thead><tr><th>단계</th><th class='n'>건</th>"
        f"<th>줄어드는 이유</th></tr></thead><tbody>{steps}</tbody></table></div>",
        f"<p class='dim'><small>근거자료 <code>{_e(pop['source'])}</code> · "
        f"회계연도 {pop['years'][0]}~{pop['years'][-1]}</small></p>",
    ]

    if not pop["lost"]:
        out.append("<p>색인에서 빠진 행은 없다. 원본의 모든 행이 검토 대상에 "
                   "들어갔다.</p>")
    else:
        for reason, items in sorted(pop["lost"].items()):
            out.append(
                f"<div class='note'><strong>{len(items)}건이 검토 대상에서 "
                f"빠졌다 — {_e(reason)}</strong><br>{_e(' / '.join(items))}"
                "<br><br>이 행들은 발견사항에도 제외 내역에도 나타나지 않는다. "
                "검토된 적이 없다는 뜻이다.</div>")
    return "\n".join(out)


def _procedures(procs: list[dict]) -> str:
    out = ["<h2>2. 적용 절차</h2>"]
    for p in procs:
        th = "".join(
            f"<tr><td>{_e(name)}</td><td>{_e(val)}</td>"
            f"<td class='dim'>{_e(why)}</td></tr>"
            for name, val, why in p["thresholds"])
        out += [
            f"<h3>{_e(p['title'])} <small class='dim'>{_e(p['rule'])}</small></h3>",
            f"<p>{_e(p['purpose'])}</p>",
            "<div class='wrap'><table>" + _rows([
                ("쓰는 자료", p["dataset"]),
                ("관점 문서", p["doc"]),
                ("살펴본 연도쌍", f"{p['examined']:,}건"),
            ]) + "</table></div>",
        ]
        if th:
            out.append(
                "<div class='wrap'><table><thead><tr><th>올리는 조건</th>"
                "<th>값</th><th>이 값인 이유</th></tr></thead>"
                f"<tbody>{th}</tbody></table></div>")
        else:
            out.append("<p>이 절차는 임계값을 밝히지 않았다. 어떤 기준으로 "
                       "걸렀는지 이 조서로는 알 수 없다.</p>")
    return "\n".join(out)


def _excluded(procs: list[dict]) -> str:
    out = [
        "<h2>3. 제외</h2>",
        "<p>살펴봤으나 올리지 않은 건과 그 이유다. 빈칸으로 두면 "
        "<em>검토하지 않았음</em>과 <em>검토했으나 해당 없음</em>이 구별되지 "
        "않는다. 감사에서 이 둘은 전혀 다른 일이다.</p>",
    ]
    for p in procs:
        counts = p["excluded"]
        if not counts:
            out.append(
                f"<div class='note'><strong>{_e(p['title'])} — 제외 기록이 "
                "없다.</strong> 정상 판정을 기록하지 않았다는 뜻이다. 임계값 "
                "아래로 걸러진 항목과 검토 후 제외한 항목을 이 조서로는 "
                "구별할 수 없다.</div>")
            continue
        total = sum(counts.values())
        body = "".join(
            f"<tr><td>{_e(reason)}</td><td class='n'>{n:,}</td>"
            f"<td class='n'>{n / total * 100:.1f}%</td>"
            f"<td style='width:8rem'><div class='bar'>"
            f"<span style='width:{n / total * 100:.1f}%'></span></div></td></tr>"
            for reason, n in counts.items())
        out += [
            f"<h3>{_e(p['title'])}</h3>",
            f"<div class='wrap'><table><thead><tr><th>제외 사유</th>"
            f"<th class='n'>건</th><th class='n'>비중</th><th></th></tr></thead>"
            f"<tbody>{body}</tbody><tfoot><tr><th>합계</th>"
            f"<td class='n'>{total:,}</td><td colspan='2'></td></tr></tfoot>"
            f"</table></div>",
        ]
    return "\n".join(out)


def _evidence(ev: list[dict]) -> str:
    if not ev:
        return ("<details><summary>원본 자료</summary><p>이 발견사항에는 원본 "
                "행이 붙어 있지 않다. 손으로 검산할 수 없다는 뜻이다.</p></details>")
    blocks = []
    for e in ev:
        cells = "".join(f"<tr><th>{_e(k)}</th><td class='n'>{_e(v)}</td></tr>"
                        for k, v in e["fields"].items())
        blocks.append(
            f"<p class='dim'><small>{_e(e['dataset'])} · {_e(e['ent_name'])} · "
            f"{_e(e['ac_year'])}년</small></p>"
            f"<div class='wrap'><table>{cells}</table></div>")
    return ("<details><summary>원본 자료 — 위 숫자가 나온 그 줄</summary>"
            + "".join(blocks) + "</details>")


def _findings(procs: list[dict]) -> str:
    out = ["<h2>4. 발견사항</h2>",
           "<p>확인이 필요한 항목이지 지적사항이 아니다. 각 건마다 계산식과 "
           "원본 행을 붙였으므로 이 조서만으로 손으로 다시 계산할 수 있다.</p>"]
    for p in procs:
        fs = p["findings"]
        if not fs:
            out.append(f"<div class='note'><strong>{_e(p['title'])} — 발견사항이 "
                       "없다.</strong> 임계값에 걸린 건이 없었다는 뜻이고, "
                       "위 3번의 제외 내역이 무엇을 봤는지 말해 준다.</div>")
            continue
        out.append(f"<h3>{_e(p['title'])} — {len(fs)}건</h3>")
        for i, f in enumerate(fs, 1):
            calc = "\n".join(f["calculation"]) or "계산식이 기록되지 않았다."
            if f["open_questions"]:
                ask = ("<p><strong>확인이 필요한 것</strong></p><ul class='ask'>"
                       + "".join(f"<li>{_e(q)}</li>" for q in f["open_questions"])
                       + "</ul>")
            else:
                ask = ("<div class='note'>확인이 필요한 항목이 비어 있다. "
                       "이 데이터로 답할 수 없는 것을 적지 않으면 질문이 아니라 "
                       "판정이 된다.</div>")
            out.append(
                f"<div class='card'><h3>{i}. {_e(f['ent_name'])} "
                f"<small class='dim'>{_e(f['ac_year'])} 회계연도</small></h3>"
                f"<p>{_e(f['headline'])}</p>"
                f"<div class='calc'>{_e(calc)}</div>{ask}{_evidence(f['evidence'])}"
                "</div>")
    return "\n".join(out)


def _limits(payload: dict) -> str:
    out = ["<h2>5. 이 조서가 말할 수 없는 것</h2>"]
    for title, body in LIMITS:
        out.append(f"<p><strong>{_e(title)}</strong><br>{_e(body)}</p>")

    for p in payload["procedures"]:
        g = p["grade_check"]
        n = len(p["findings"])
        if not n:
            continue
        out.append(
            f"<p><strong>{_e(p['title'])} — 행정안전부 경영평가 등급과 맞춰 본 "
            f"결과</strong><br>발견사항 {n}건 중 등급을 대조할 수 있는 것이 "
            f"{g['comparable']}건이고, 그중 하위등급(라·마)은 {g['low']}건이다. "
            "등급이 높은데 이 절차가 올린 것을 오답이라 부를 수는 없다 — "
            "경영평가는 그 해 경영 전반을 보고 이 절차는 부채 만기 하나를 본다. "
            "두 질문이 겹치지 않는다.</p>")
    return "\n".join(out)


def render(payload: dict) -> str:
    pop = payload["population"]
    t = payload["totals"]
    meta = [
        ("검토 대상", payload["subject"]),
        ("근거자료", pop["source"]),
        ("회계연도", f"{pop['years'][0]}~{pop['years'][-1]}"),
        ("살펴본 건", f"{t['examined']:,}건"),
        ("발견사항", f"{t['findings']:,}건"),
        ("제외", f"{t['excluded']:,}건"),
    ]
    dl = "".join(f"<dt>{_e(k)}</dt><dd>{_e(v)}</dd>" for k, v in meta)

    body = "\n".join([
        _population(pop),
        _procedures(payload["procedures"]),
        _excluded(payload["procedures"]),
        _findings(payload["procedures"]),
        _limits(payload),
    ])

    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>검토조서 — {_e(payload['subject'])}</title>
<style>{CSS}</style></head><body><main>
<header>
<h1>검토조서</h1>
<p class="dim">{_e(payload['subject'])}</p>
<dl class="meta">{dl}</dl>
<p class="dim"><small>작성일시를 넣지 않는다. 실행 시각을 찍으면 같은 자료에서
매번 다른 바이트가 나오고, 조서를 저장소에 커밋해 두므로 그러면 무엇이 바뀌었는지
알 수 없게 된다. 조서가 무엇을 근거로 만들어졌는지는 위 회계연도가 말해 준다.</small></p>
</header>
{body}
</main></body></html>
"""
