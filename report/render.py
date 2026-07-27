"""조서 payload → 단일 HTML 파일.

## 렌더러는 계산도 판단도 하지 않는다

내용은 `screen/` 이 만들고 `workpaper.py` 가 칸에 담는다. 여기서는 **읽는
순서와 읽는 법만** 정한다. 렌더러가 요약하거나 보태기 시작하면 화면에 보이는
것과 코드가 계산한 것이 갈라지고, 그때부터 "이렇게 검토했다"는 말에 근거가
없다. 그래서 이 모듈은 `screen` 을 import 하지 않는다 -- 테스트가 확인한다.

발견사항의 문장·계산식·확인이 필요한 것은 한 글자도 바꾸지 않는다. 여기서
더하는 것은 **읽는 법**뿐이다. 절차가 무엇을 보는지 쉬운 말로 옮긴 문장과
용어 풀이는 규칙 모듈이 소유하고(`PLAIN`, `TERMS`), 이 파일은 그것을 어디에
놓을지만 정한다.

## 칸의 순서

감사조서의 순서를 따른다. 다만 한 군데를 바꿨다.

    1  모집단      무엇을 다 봤다고 말하는가
    2  적용 절차   어떤 눈으로 봤는가, 임계값은 어디서 왔는가
    3  제외        올리지 않은 것과 그 이유
    4  발견사항    올린 것
    5  한계        이 조서가 확인해 주지 않는 것

**제외가 발견사항보다 앞이다.** 발견사항을 먼저 놓으면 읽는 사람은 거기서
멈추고, 조서에서 정작 방어해야 하는 것은 "그럼 저기는 왜 안 봤나" 쪽이다.

## 누가 읽어도 이해되게

ISA 230 이 말하는 문서화의 기준은 *경험 있는 제3의 감사인이 이해할 수 있도록*
이다. 이 조서는 한 칸 더 간다 -- 회계를 모르는 사람이 읽어도 무엇을 왜 봤는지
알 수 있어야 한다.

서식을 풀어 버리면 조서가 아니게 되고, 용어만 두면 읽을 사람이 감사인으로
좁혀진다. 그래서 **서식은 그대로 두고 용어에 풀이를 붙인다.**

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
:root{
  --bg:#faf9f6; --surface:#fff; --sunk:#f4f2ed;
  --ink:#14161a; --body:#33373e; --dim:#7b8089; --faint:#a8adb5;
  --line:#e6e2d9; --hair:#f0ede6;
  --accent:#1d4e5a; --accent-soft:#e8f0f1;
  --alert:#8f3f34; --alert-soft:#fbf1ef;
  --radius:10px;
}
@media (prefers-color-scheme:dark){
  :root{
    --bg:#111317; --surface:#181b20; --sunk:#1e2126;
    --ink:#f0eee9; --body:#c6c9ce; --dim:#8b9098; --faint:#666b73;
    --line:#282c33; --hair:#212429;
    --accent:#7fb8c4; --accent-soft:#16282d;
    --alert:#d99184; --alert-soft:#2a1d1b;
  }
}
*{box-sizing:border-box;}
html{-webkit-text-size-adjust:100%;}
body{
  margin:0; padding:0 1.5rem 7rem; background:var(--bg); color:var(--body);
  font:400 16px/1.85 "Pretendard","Apple SD Gothic Neo","Malgun Gothic",
       "맑은 고딕",-apple-system,BlinkMacSystemFont,sans-serif;
  letter-spacing:-.011em; word-break:keep-all; overflow-wrap:break-word;
}
main{max-width:50rem; margin:0 auto;}
h1,h2,h3,h4{color:var(--ink); line-height:1.35; letter-spacing:-.025em;}
p{margin:.85rem 0;}
b,strong{color:var(--ink); font-weight:600;}
em{font-style:normal; color:var(--accent); font-weight:500;}
code{font-family:"SFMono-Regular",Consolas,"D2Coding",monospace;
     font-size:.86em; color:var(--dim);}
.dim{color:var(--dim);}
.tiny{font-size:.8rem; line-height:1.7;}

/* ── 표지 ───────────────────────────────────────────── */
header{padding:5.5rem 0 0;}
.kicker{font-size:.72rem; letter-spacing:.22em; text-transform:uppercase;
        color:var(--accent); font-weight:600; margin:0 0 1.1rem;}
h1{font-size:clamp(2rem,5.5vw,2.9rem); margin:0; font-weight:700;}
.sub{font-size:1.05rem; color:var(--dim); margin:.7rem 0 0;}

.stats{display:grid; grid-template-columns:repeat(3,1fr); gap:1px;
       background:var(--line); border:1px solid var(--line);
       border-radius:var(--radius); overflow:hidden; margin:2.75rem 0 1.25rem;}
.stat{background:var(--surface); padding:1.35rem 1.25rem;}
.stat b{display:block; font-size:1.85rem; font-weight:700; line-height:1.15;
        font-variant-numeric:tabular-nums; letter-spacing:-.03em;}
.stat span{display:block; font-size:.78rem; color:var(--dim); margin-top:.3rem;}
.stat em{font-size:.72rem; color:var(--faint); font-weight:400;}

.facts{display:grid; grid-template-columns:max-content 1fr; gap:.3rem 1.5rem;
       font-size:.85rem; margin:0; padding:1.35rem 0 0;
       border-top:1px solid var(--hair);}
.facts dt{color:var(--faint);}
.facts dd{margin:0; color:var(--body);}

/* ── 섹션 ───────────────────────────────────────────── */
section{margin-top:5rem;}
h2{display:flex; align-items:baseline; gap:.75rem; font-size:1.4rem;
   margin:0 0 .2rem; padding-bottom:1rem; border-bottom:1px solid var(--ink);}
h2 i{font-style:normal; font-size:.78rem; font-weight:600; color:var(--accent);
     font-variant-numeric:tabular-nums;}
.lede{font-size:.95rem; color:var(--dim); margin:1.1rem 0 0;}
h3{font-size:1.02rem; margin:2.5rem 0 .6rem; font-weight:650;}
h3 small{font-weight:400; color:var(--faint); font-size:.78rem;
         margin-left:.4rem; font-family:Consolas,monospace;}

/* ── 표 ─────────────────────────────────────────────── */
.wrap{overflow-x:auto; margin:1.4rem 0;
      border:1px solid var(--line); border-radius:var(--radius);
      background:var(--surface);}
table{border-collapse:collapse; width:100%; font-size:.88rem;}
th,td{text-align:left; padding:.72rem 1rem; vertical-align:top;
      border-bottom:1px solid var(--hair);}
thead th{font-size:.73rem; font-weight:600; color:var(--faint);
         letter-spacing:.06em; text-transform:uppercase; white-space:nowrap;
         background:var(--sunk);}
tbody tr:last-child td,tbody tr:last-child th{border-bottom:none;}
tfoot td,tfoot th{border-top:1px solid var(--line); border-bottom:none;
                  font-weight:600; color:var(--ink); background:var(--sunk);}
td.n,th.n{text-align:right; font-variant-numeric:tabular-nums;
          white-space:nowrap;}
tbody th{font-weight:500; color:var(--dim); white-space:nowrap;}
.step td:first-child{font-weight:500; color:var(--ink);}

/* ── 강조 상자 ──────────────────────────────────────── */
.flag{background:var(--alert-soft); border:1px solid var(--alert);
      border-radius:var(--radius); padding:1.15rem 1.35rem; margin:1.5rem 0;
      font-size:.89rem; color:var(--body);}
.flag b{display:block; color:var(--alert); margin-bottom:.45rem;
        font-size:.95rem;}
.flag .items{font-family:Consolas,monospace; font-size:.8rem;
             color:var(--dim); margin:.5rem 0;}
.plain{background:var(--accent-soft); border-radius:var(--radius);
       padding:1.1rem 1.35rem; margin:1.2rem 0; font-size:.93rem;}
.plain b{color:var(--accent);}

/* ── 제외 막대 ──────────────────────────────────────── */
.bars{margin:1.4rem 0;}
.row{display:grid; grid-template-columns:1fr auto; gap:.15rem .9rem;
     align-items:baseline; padding:.85rem 0; border-bottom:1px solid var(--hair);}
.row:last-child{border-bottom:none;}
.row .lbl{font-size:.9rem; color:var(--ink);}
.row .val{font-size:.85rem; color:var(--dim); font-variant-numeric:tabular-nums;
          white-space:nowrap;}
.row .track{grid-column:1/-1; height:3px; background:var(--hair);
            border-radius:2px; margin-top:.4rem;}
.row .track i{display:block; height:100%; background:var(--accent);
              border-radius:2px;}

/* ── 발견사항 ───────────────────────────────────────── */
.find{background:var(--surface); border:1px solid var(--line);
      border-radius:var(--radius); padding:1.6rem 1.75rem; margin:1.25rem 0;}
.find header{display:flex; align-items:baseline; gap:.6rem; padding:0;
             margin-bottom:.9rem; flex-wrap:wrap;}
.find .idx{font-size:.72rem; font-weight:700; color:var(--faint);
           font-variant-numeric:tabular-nums;}
.find h4{font-size:1.12rem; margin:0; font-weight:650;}
.find .yr{font-size:.78rem; color:var(--dim);}
.find .lead{margin:0 0 1rem; font-size:.95rem;}
.scale{height:3px; background:var(--hair); border-radius:2px; margin:0 0 1.2rem;}
.scale i{display:block; height:100%; background:var(--accent); border-radius:2px;}
.calc{background:var(--sunk); border-radius:8px; padding:1rem 1.2rem;
      margin:1rem 0; font-family:"SFMono-Regular",Consolas,"D2Coding",monospace;
      font-size:.8rem; line-height:2; white-space:pre-wrap; overflow-x:auto;
      color:var(--body);}
.ask{margin:1.2rem 0 0; padding:0; list-style:none;}
.ask li{position:relative; padding-left:1.15rem; margin:.5rem 0;
        font-size:.89rem;}
.ask li::before{content:"?"; position:absolute; left:0; top:0;
                color:var(--accent); font-weight:700; font-size:.85rem;}
.label{font-size:.72rem; letter-spacing:.1em; text-transform:uppercase;
       color:var(--faint); font-weight:600; margin:0;}

details{margin-top:1.3rem; border-top:1px solid var(--hair); padding-top:.9rem;}
summary{cursor:pointer; font-size:.82rem; color:var(--dim); list-style:none;
        display:flex; align-items:center; gap:.4rem;}
summary::-webkit-details-marker{display:none;}
summary::before{content:"+"; color:var(--accent); font-weight:700;}
details[open] summary::before{content:"−";}
details .wrap{margin:.9rem 0 .3rem;}
details table{font-size:.78rem;}

/* ── 한계 ───────────────────────────────────────────── */
.limit{border-top:1px solid var(--hair); padding:1.35rem 0;}
.limit:first-of-type{border-top:none;}
.limit b{display:block; font-size:.98rem; margin-bottom:.35rem;}
.limit p{margin:0; font-size:.9rem;}

footer{margin-top:5rem; padding-top:1.5rem; border-top:1px solid var(--hair);
       font-size:.78rem; color:var(--faint); line-height:1.8;}

@media (max-width:34rem){
  body{padding:0 1.1rem 4rem; font-size:15px;}
  .stats{grid-template-columns:1fr;}
  .find{padding:1.25rem 1.15rem;}
  .facts{grid-template-columns:1fr; gap:.1rem;}
  .facts dd{margin-bottom:.6rem;}
}

@media print{
  :root{--bg:#fff; --surface:#fff; --sunk:#fff; --ink:#000; --body:#222;
        --dim:#555; --faint:#777; --line:#bbb; --hair:#ddd;
        --accent:#000; --accent-soft:#fff; --alert:#000; --alert-soft:#fff;}
  body{padding:0; font-size:10pt;}
  header{padding-top:0;}
  section{margin-top:2.5rem; break-inside:auto;}
  h2{break-after:avoid;}
  .find,.flag,.wrap,.plain{break-inside:avoid; border:1px solid #bbb;}
  details{break-inside:avoid;}
  details summary::before{content:"";}
  details > *:not(summary){display:block !important;}
}
"""

# 조서 서식 자체의 말. 처음 읽는 사람은 '모집단'에서 먼저 막힌다.
FRAME_TERMS = [
    ("모집단", "빠짐없이 다 봤다고 말하는 대상의 범위"),
    ("연도쌍", "같은 기관의 올해와 작년을 한 쌍으로 묶은 것. 변화를 보려면 두 해가 필요하다"),
    ("제외", "살펴봤지만 올리지 않은 건. 안 본 것과 다르다"),
    ("발견사항", "확인이 필요하다고 올린 건. 잘못했다는 판정이 아니다"),
]

# 조서가 스스로 밝혀야 하는 한계. 밖에 적어 두면 조서만 받은 사람은
# 확인이 끝난 도구로 읽는다.
LIMITS = [
    ("올린 것이 맞는지 채점된 적이 없다",
     "감사원이 이 기관들을 표제로 감사한 것은 2020년 이후 7건뿐이고, 그 감사가 "
     "본 회계연도가 여기서 검토한 연도와 겹치지 않는다. 맞혔는지 대조할 자료가 "
     "없다는 뜻이다."),
    ("정밀도는 애초에 잴 수 없다",
     "올린 건에 감사 기록이 없을 때 '문제가 없었다'와 '아무도 안 들여다봤다'는 "
     "공개 자료로 구별되지 않는다. 그래서 이 조서는 적중률을 숫자로 내지 않는다. "
     "낼 수 없는 숫자를 내는 것이 못 내는 것보다 나쁘다."),
    ("이 도구는 판정하지 않는다",
     "발견사항은 확인이 필요한 항목이지 지적사항이 아니다. 각 건에 붙은 '확인이 "
     "필요한 것'은 이 데이터로 답할 수 없어 사람에게 넘기는 질문이다."),
]

READING = ("이 조서는 <b>무엇을 올렸는지보다 무엇을 안 올렸는지</b>를 먼저 "
           "보여 준다. 감사 대상을 고를 때 정작 답하기 어려운 질문은 "
           "&ldquo;왜 저기를 봤나&rdquo;가 아니라 "
           "<b>&ldquo;그럼 저기는 왜 안 봤나&rdquo;</b>이기 때문이다. "
           "그래서 3번 칸(제외)이 4번 칸(발견사항)보다 앞에 있다.")


def _e(v: Any) -> str:
    """HTML 이스케이프. 기관명과 원본 값이 그대로 들어가므로 전부 통과시킨다."""
    return html.escape("" if v is None else str(v), quote=True)


def _mark(text: str) -> str:
    """*별표* 로 감싼 곳만 강조한다. 이스케이프한 뒤에 바꾸므로 본문에 든
    태그는 그대로 글자로 남는다."""
    parts = _e(text).split("*")
    return "".join(p if i % 2 == 0 else f"<b>{p}</b>"
                   for i, p in enumerate(parts))


def _kv(pairs: list[tuple[str, Any]]) -> str:
    body = "".join(f"<tr><th>{_e(k)}</th><td>{_e(v)}</td></tr>" for k, v in pairs)
    return f"<div class='wrap'><table><tbody>{body}</tbody></table></div>"


def _terms(pairs: list[tuple[str, str]], caption: str) -> str:
    if not pairs:
        return ""
    body = "".join(f"<tr><th>{_e(t)}</th><td>{_e(d)}</td></tr>" for t, d in pairs)
    return (f"<p class='label'>{_e(caption)}</p>"
            f"<div class='wrap'><table><tbody>{body}</tbody></table></div>")


def _section(num: int, title: str, lede: str, body: str) -> str:
    return (f"<section><h2><i>{num:02d}</i>{_e(title)}</h2>"
            f"<p class='lede'>{lede}</p>{body}</section>")


def _population(pop: dict) -> str:
    steps = "".join(
        f"<tr class='step'><td>{_e(label)}</td><td class='n'>{n:,}</td>"
        f"<td class='dim'>{_e(why)}</td></tr>"
        for label, n, why in pop["steps"])

    out = [
        "<div class='wrap'><table><thead><tr><th>단계</th><th class='n'>건</th>"
        f"<th>여기서 줄어드는 이유</th></tr></thead><tbody>{steps}</tbody>"
        "</table></div>",
        _terms(FRAME_TERMS, "이 조서가 쓰는 말"),
    ]

    if not pop["lost"]:
        out.append("<p>색인에서 빠진 행은 없다. 원본 파일의 모든 행이 검토 "
                   "대상에 들어갔다.</p>")
    else:
        for reason, items in sorted(pop["lost"].items()):
            out.append(
                f"<div class='flag'><b>{len(items)}건이 검토 대상에서 빠졌다 "
                f"— {_e(reason)}</b>"
                f"<div class='items'>{_e(' · '.join(items))}</div>"
                "이 행들은 발견사항에도 제외 내역에도 나타나지 않는다. "
                "<b style='display:inline'>검토된 적이 없다</b>는 뜻이다. "
                "고쳐서 감추지 않고 여기에 띄운다.</div>")
    return "\n".join(out)


def _procedures(procs: list[dict]) -> str:
    out = []
    for p in procs:
        out.append(f"<h3>{_e(p['title'])}<small>{_e(p['rule'])}</small></h3>")
        out.append(f"<p>{_e(p['purpose'])}</p>")
        if p.get("plain"):
            out.append("<div class='plain'><b>쉬운 말로 —</b> "
                       f"{_mark(p['plain'])}</div>")
        out.append(_kv([("쓰는 자료", p["dataset"]),
                        ("관점 문서", p["doc"]),
                        ("살펴본 연도쌍", f"{p['examined']:,}건")]))
        out.append(_terms(p.get("terms", []), "이 절차가 쓰는 말"))

        if p["thresholds"]:
            rows = "".join(
                f"<tr><td>{_e(name)}</td><td class='n'>{_e(val)}</td>"
                f"<td class='dim'>{_e(why)}</td></tr>"
                for name, val, why in p["thresholds"])
            out.append(
                "<p class='label'>이 셋을 모두 넘겨야 올린다</p>"
                "<div class='wrap'><table><thead><tr><th>조건</th>"
                "<th class='n'>기준</th><th>왜 이 값인가</th></tr></thead>"
                f"<tbody>{rows}</tbody></table></div>")
        else:
            out.append("<p>이 절차는 임계값을 밝히지 않았다. 어떤 기준으로 "
                       "걸렀는지 이 조서로는 알 수 없다.</p>")
    return "\n".join(out)


def _excluded(procs: list[dict]) -> str:
    out = []
    for p in procs:
        counts = p["excluded"]
        if not counts:
            out.append(
                f"<div class='flag'><b>{_e(p['title'])} — 제외 기록이 없다</b>"
                "정상 판정을 기록하지 않았다는 뜻이다. 임계값 아래로 걸러진 "
                "항목과 검토 후 제외한 항목을 이 조서로는 구별할 수 없다.</div>")
            continue
        total = sum(counts.values())
        rows = "".join(
            f"<div class='row'><span class='lbl'>{_e(reason)}</span>"
            f"<span class='val'>{n:,}건 · {n / total * 100:.1f}%</span>"
            f"<span class='track'><i style='width:{n / total * 100:.1f}%'></i>"
            f"</span></div>"
            for reason, n in counts.items())
        out += [
            f"<h3>{_e(p['title'])}</h3>",
            f"<div class='bars'>{rows}</div>",
            f"<p class='tiny dim'>합계 {total:,}건. 이 표가 있어야 "
            "<em>검토하지 않았음</em>과 <em>검토했으나 해당 없음</em>이 "
            "구별된다.</p>",
        ]
    return "\n".join(out)


def _evidence(ev: list[dict]) -> str:
    if not ev:
        return ("<details><summary>원본 자료</summary><p class='tiny'>이 "
                "발견사항에는 원본 행이 붙어 있지 않다. 손으로 검산할 수 없다는 "
                "뜻이다.</p></details>")
    blocks = []
    for e in ev:
        cells = "".join(f"<tr><th>{_e(k)}</th><td class='n'>{_e(v)}</td></tr>"
                        for k, v in e["fields"].items())
        blocks.append(
            f"<p class='label'>{_e(e['dataset'])} · {_e(e['ent_name'])} · "
            f"{_e(e['ac_year'])}년</p>"
            f"<div class='wrap'><table><tbody>{cells}</tbody></table></div>")
    return ("<details><summary>원본 자료 — 위 숫자가 나온 그 줄</summary>"
            + "".join(blocks) + "</details>")


def _findings(procs: list[dict]) -> str:
    out = []
    for p in procs:
        fs = p["findings"]
        if not fs:
            out.append(
                f"<div class='flag'><b>{_e(p['title'])} — 발견사항이 없다</b>"
                "임계값에 걸린 건이 없었다는 뜻이고, 3번 칸의 제외 내역이 "
                "무엇을 봤는지 말해 준다.</div>")
            continue
        top = max((f["magnitude"] for f in fs), default=0) or 1
        out.append(f"<h3>{_e(p['title'])} — {len(fs)}건</h3>")
        for i, f in enumerate(fs, 1):
            calc = "\n".join(f["calculation"]) or "계산식이 기록되지 않았다."
            if f["open_questions"]:
                ask = ("<p class='label'>사람이 확인해야 하는 것</p>"
                       "<ul class='ask'>"
                       + "".join(f"<li>{_e(q)}</li>" for q in f["open_questions"])
                       + "</ul>")
            else:
                ask = ("<div class='flag'><b>확인이 필요한 항목이 비어 있다</b>"
                       "이 데이터로 답할 수 없는 것을 적지 않으면 질문이 아니라 "
                       "판정이 된다.</div>")
            width = max(f["magnitude"] / top * 100, 1.5)
            out.append(
                "<article class='find'>"
                f"<header><span class='idx'>{i:02d}</span>"
                f"<h4>{_e(f['ent_name'])}</h4>"
                f"<span class='yr'>{_e(f['ac_year'])} 회계연도</span></header>"
                f"<p class='lead'>{_e(f['headline'])}</p>"
                f"<div class='scale'><i style='width:{width:.1f}%'></i></div>"
                "<p class='label'>손으로 다시 계산해 볼 수 있게</p>"
                f"<div class='calc'>{_e(calc)}</div>{ask}"
                f"{_evidence(f['evidence'])}</article>")
    return "\n".join(out)


def _limits(payload: dict) -> str:
    out = [f"<div class='limit'><b>{_e(t)}</b><p>{_e(b)}</p></div>"
           for t, b in LIMITS]

    for p in payload["procedures"]:
        g = p["grade_check"]
        n = len(p["findings"])
        if not n:
            continue
        out.append(
            "<div class='limit'><b>행정안전부 경영평가 등급과 맞춰 본 결과 — "
            f"{_e(p['title'])}</b><p>발견사항 {n}건 중 등급을 대조할 수 있는 "
            f"것이 {g['comparable']}건이고, 그중 하위등급(라·마)은 "
            f"{g['low']}건이다. 등급이 높은데 이 절차가 올린 것을 오답이라 "
            "부를 수는 없다 — 경영평가는 그 해 경영 전반을 보고 이 절차는 "
            "부채 만기 하나를 본다. 두 질문이 겹치지 않는다.</p></div>")
    return "\n".join(out)


def render(payload: dict) -> str:
    pop = payload["population"]
    t = payload["totals"]
    span = f"{pop['years'][0]}~{pop['years'][-1]}"

    stats = "".join([
        f"<div class='stat'><b>{t['examined']:,}</b>"
        "<span>살펴본 연도쌍</span><em>빠짐없이 전수</em></div>",
        f"<div class='stat'><b>{t['excluded']:,}</b>"
        "<span>제외</span><em>사유를 세어서 남김</em></div>",
        f"<div class='stat'><b>{t['findings']:,}</b>"
        "<span>발견사항</span><em>확인이 필요한 건</em></div>",
    ])
    facts = "".join(f"<dt>{_e(k)}</dt><dd>{_e(v)}</dd>" for k, v in [
        ("검토 대상", payload["subject"]),
        ("근거자료", pop["source"]),
        ("회계연도", span),
        ("적용 절차", f"{len(payload['procedures'])}개"),
    ])

    body = "\n".join([
        _section(1, "모집단",
                 "원본 파일에서 살펴본 연도쌍까지 수가 어떻게 줄어드는지 적는다. "
                 "중간에 사라진 행이 있으면 여기서 드러난다.",
                 _population(pop)),
        _section(2, "적용 절차",
                 "어떤 눈으로 봤는지, 그리고 올리는 기준을 어디서 가져왔는지.",
                 _procedures(payload["procedures"])),
        _section(3, "제외",
                 "살펴봤으나 올리지 않은 건과 그 이유다. 빈칸으로 두면 "
                 "<em>검토하지 않았음</em>과 <em>검토했으나 해당 없음</em>이 "
                 "구별되지 않는다. 감사에서 이 둘은 전혀 다른 일이다.",
                 _excluded(payload["procedures"])),
        _section(4, "발견사항",
                 "확인이 필요한 항목이지 지적사항이 아니다. 각 건에 계산식과 "
                 "원본 행을 붙였으므로 이 조서만으로 손으로 다시 계산할 수 있다.",
                 _findings(payload["procedures"])),
        _section(5, "이 조서가 말할 수 없는 것",
                 "여기 적지 않으면 조서를 받은 사람은 확인이 끝난 도구로 읽는다.",
                 _limits(payload)),
    ])

    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>검토조서 — {_e(payload['subject'])}</title>
<meta name="description" content="지방공기업 결산자료를 전수로 훑어 확인이 필요한 항목을 고른 검토조서">
<style>{CSS}</style></head><body><main>
<header>
<p class="kicker">Working Paper</p>
<h1>검토조서</h1>
<p class="sub">{_e(payload['subject'])}</p>
<div class="stats">{stats}</div>
<dl class="facts">{facts}</dl>
</header>
<section><p class="lede">{READING}</p></section>
{body}
<footer>
작성일시를 넣지 않는다. 실행 시각을 찍으면 같은 자료에서 매번 다른 바이트가
나오고, 이 조서를 저장소에 커밋해 두므로 그러면 무엇이 바뀌었는지 알 수 없게
된다. 조서가 무엇을 근거로 만들어졌는지는 위 회계연도({_e(span)})가 말해 준다.
<br><br>
이 문서는 외부 스크립트·스타일·폰트를 하나도 참조하지 않는다. 첨부해서 보내도,
인터넷 없이 열어도, 5년 뒤에 열어도 같은 문서다.
</footer>
</main></body></html>
"""
