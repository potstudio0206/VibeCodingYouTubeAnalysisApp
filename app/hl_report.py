# -*- coding: utf-8 -*-
"""HTMLレポートとテキストメモの出力"""
import json
import os

from hl_analyze import fmt


def write_report(res, info, vdir):
    data = {
        "vid": info["id"], "title": info.get("title") or info["id"],
        "channel": info.get("channel", ""), **res,
    }
    js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.replace("__DATA__", js).replace("__TITLE__", _esc(data["title"]))
    path = os.path.join(vdir, "見どころレポート.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)

    lines = [data["title"], ""]
    if res["phases"]:
        lines.append("■ パート")
        for p in res["phases"]:
            lines.append(f"{fmt(p['start'])}〜{fmt(p['end'])}  {p['name']}")
        lines.append("")
    if res["matches"]:
        lines.append(f"■ 試合（{len(res['matches'])}試合）")
        for m in res["matches"]:
            st = m["stats"] or {}
            best = f"  見どころ {fmt(st['best'])}" if st.get("best") is not None else ""
            lines.append(f"試合{m['no']:>2}  {fmt(m['start'])}〜{fmt(m['end'])}  最大スコア{st.get('score_max', '-')}{best}")
        lines.append("")
    lines.append("■ 見どころ候補（時系列）")
    for h in sorted(res["highlights"], key=lambda h: h["start"]):
        where = f"試合{h['match']}" if h["match"] else ("序盤" if h["phase"] == "practice" else "")
        msgs = "、".join(f"「{k}」×{n}" for k, n in h["top"][:3])
        lines.append(f"{fmt(h['start'])}  [{where or '-'}] スコア{h['score']}  {' / '.join(h['reasons'])}"
                     + (f"  {msgs}" if msgs else ""))
    with open(os.path.join(vdir, "見どころメモ.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def _esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


TEMPLATE = r"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>見どころレポート - __TITLE__</title>
<style>
:root{--bg:#0f1115;--card:#181b22;--card2:#20242d;--fg:#e8eaf0;--sub:#9aa3b2;--line:#2a2f3a;
  --accent:#ff4d6d;--link:#7cc4ff;--practice:#2bb3a3;--ranked:#8b6cf0;--gold:#ffd166}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font-family:"Yu Gothic UI","Meiryo",system-ui,sans-serif;font-size:14px}
.wrap{max-width:1280px;margin:0 auto;padding:24px 16px 60px}
h1{font-size:20px;margin:0 0 4px}
h2{font-size:15px;margin:0 0 12px}
.meta{color:var(--sub);font-size:13px;margin-bottom:18px}
a{color:var(--link)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:16px}
.sub{color:var(--sub);font-size:12px}
.note{color:var(--sub);font-size:12px;margin-top:8px}
.warn{color:var(--gold)}
/* パート比較 */
.cmp{display:grid;grid-template-columns:150px 1fr 1fr 110px;gap:0;font-variant-numeric:tabular-nums}
.cmp>div{padding:8px 10px;border-bottom:1px solid var(--line)}
.cmp .h{color:var(--sub);font-size:12px}
.cmp .p{border-left:3px solid var(--practice)} .cmp .r{border-left:3px solid var(--ranked)}
.diff-up{color:var(--accent)} .diff-down{color:var(--link)}
/* タイムライン */
.tl-head{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px}
.spacer{flex:1}
.chip{padding:4px 12px;border-radius:999px;border:1px solid var(--line);background:transparent;color:var(--fg);font-size:12px;cursor:pointer;font-family:inherit}
.chip:hover{background:var(--card2)} .chip.on{border-color:var(--accent);color:var(--accent)}
select{background:var(--card2);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:4px 8px;font-family:inherit}
.tl{position:relative}
#tl{width:100%;display:block;cursor:crosshair}
#tip{position:absolute;pointer-events:none;background:#000d;border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:12px;
  line-height:1.6;display:none;white-space:nowrap;z-index:5;font-variant-numeric:tabular-nums}
.legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:8px;color:var(--sub);font-size:12px;align-items:center}
.sw{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-2px;margin-right:4px}
.grad{display:inline-block;width:120px;height:10px;border-radius:3px;vertical-align:-1px;margin:0 6px}
/* 表 */
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
th,td{padding:8px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}
th{color:var(--sub);font-weight:normal;font-size:12px;white-space:nowrap}
.scroll{overflow-x:auto}
.bar{min-width:80px}
.bar i{display:block;height:4px;margin-top:4px;border-radius:2px;background:var(--accent);opacity:.6}
tr.mrow{cursor:pointer} tr.mrow:hover td{background:var(--card2)}
.time{color:var(--link);font-weight:bold;text-decoration:none;font-size:15px}
.time:hover{text-decoration:underline}
.badge{display:inline-block;font-size:11px;padding:1px 8px;border-radius:999px;margin-right:4px;white-space:nowrap}
.b-practice{background:#2bb3a333;color:var(--practice)} .b-ranked{background:#8b6cf033;color:#b9a6ff}
.score{color:var(--accent);font-weight:bold}
.chips2 span{display:inline-block;background:var(--card2);border-radius:999px;padding:1px 8px;margin:4px 4px 0 0;font-size:12px}
tr.seen td{opacity:.45}
</style></head><body><div class="wrap">
<h1 id="title"></h1>
<div class="meta" id="meta"></div>

<div class="card" id="cmpCard">
  <h2>序盤（雑談・練習） と 後半（実践） の比較</h2>
  <div id="cmp"></div>
</div>

<div class="card">
  <div class="tl-head">
    <h2 style="margin:0">タイムライン</h2>
    <span class="spacer"></span>
    <button class="chip on" id="mHeat">ヒートマップ</button><button class="chip" id="mLine">折れ線</button>
    <select id="zoom"></select>
  </div>
  <div class="tl"><canvas id="tl"></canvas><div id="tip"></div></div>
  <div class="legend" id="legend"></div>
  <div class="note">クリックすると、その時刻の少し前からYouTubeで開きます。ヒートマップの色は、その配信の中での相対的な高さ（明るいほど高い）です。</div>
</div>

<div class="card" id="matchCard">
  <h2 id="matchTitle">試合ごと</h2>
  <div class="scroll"><table><thead><tr>
    <th>試合</th><th>開始</th><th>長さ</th><th>コメント/分</th><th>同じコメント</th><th>声の大きさ</th><th>喋る量</th><th>最大スコア</th><th>見どころ</th>
  </tr></thead><tbody id="mt"></tbody></table></div>
  <div class="note">行をクリックすると、タイムラインがその試合に拡大されます。</div>
</div>

<div class="card">
  <div class="tl-head">
    <h2 style="margin:0">見どころ候補</h2><span class="spacer"></span>
    <span id="filters"></span>
    <button class="chip on" id="sScore">スコア順</button><button class="chip" id="sTime">時系列順</button>
  </div>
  <div class="scroll"><table><thead><tr><th>#</th><th>確認開始</th><th>場所</th><th>スコア</th><th>理由・多かったコメント</th></tr></thead>
  <tbody id="hl"></tbody></table></div>
</div>
</div>

<script>
const D = __DATA__;
const $ = id => document.getElementById(id);
const fmt = s => { s = Math.max(0, Math.floor(s)); return `${Math.floor(s/3600)}:${String(Math.floor(s%3600/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`; };
const fmtDur = s => { s = Math.round(s); const h=Math.floor(s/3600), m=Math.floor(s%3600/60), ss=s%60; return h ? `${h}時間${m}分` : (m ? `${m}分${String(ss).padStart(2,'0')}秒` : `${ss}秒`); };
const yt = t => `https://www.youtube.com/watch?v=${D.vid}&t=${Math.max(0, Math.floor(t))}s`;
const el = (tag, cls, text) => { const e=document.createElement(tag); if(cls) e.className=cls; if(text!=null) e.textContent=text; return e; };
const link = (t, label) => { const a=el('a','time',label ?? fmt(t)); a.href=yt(t); a.target='_blank'; return a; };

// ---------- ヘッダー
$('title').textContent = D.title;
{
  const m = $('meta');
  const parts = [D.channel, `長さ ${fmtDur(D.duration)}`];
  if (D.has.chat) parts.push(`コメント ${D.total.toLocaleString()}件`);
  if (D.matches.length) parts.push(`試合 ${D.matches.length}`);
  m.append(parts.filter(Boolean).join('　') + '　');
  const a = el('a', null, '動画を開く'); a.href = yt(0); a.target = '_blank'; m.append(a);
  const miss = [];
  if (!D.has.chat) miss.push('チャット');
  if (!D.has.audio) miss.push('声');
  if (!D.has.video) miss.push('画面（試合の区切り）');
  if (miss.length) { m.append(el('br')); m.append(el('span','warn',`※ ${miss.join('・')}は解析していません`)); }
  else if (!D.matches.length) { m.append(el('br')); m.append(el('span','warn','※ 画面から「RANKED MATCH」が見つからなかったため、パートと試合の区切りはありません')); }
}

// ---------- パート比較
(function renderCmp(){
  const P = D.phases.find(p => p.key==='practice'), R = D.phases.find(p => p.key==='ranked');
  if (!P || !R || !P.stats || !R.stats) { $('cmpCard').style.display='none'; return; }
  const box = $('cmp'); box.className = 'cmp';
  const head = ['', '序盤（雑談・練習）', '後半（実践）', '後半は'];
  head.forEach((t,i) => box.append(el('div', 'h' + (i===1?' p':i===2?' r':''), t)));
  const rows = [
    ['時間帯', s => `${fmt(s.start)}〜${fmt(s.end)}`, null],
    ['長さ', s => fmtDur(s.end - s.start), null],
    ['コメント/分', s => s.cpm, 'ratio'],
    ['同じコメント率', s => s.same==null?null:s.same+'%', 'pt', s => s.same],
    ['声の大きさ（平均）', s => s.loud==null?null:s.loud+' dB', 'db', s => s.loud],
    ['喋る量', s => s.talk==null?null:s.talk+'%', 'pt', s => s.talk],
    ['平均スコア', s => s.score_avg, 'ratio'],
    ['見どころ候補', s => s.highlights+'か所', null],
    ['多かったワード', s => s.kw_top || '—', null],
  ];
  for (const [label, f, kind, raw] of rows) {
    const a = f(P.stats), b = f(R.stats);
    if (a == null && b == null) continue;
    box.append(el('div', 'h', label), el('div', 'p', a ?? '—'), el('div', 'r', b ?? '—'));
    let d = '';
    const va = raw ? raw(P.stats) : a, vb = raw ? raw(R.stats) : b;
    let cls = '';
    if (kind && va != null && vb != null) {
      if (kind==='ratio' && va > 0) { const r = vb/va; d = `${r.toFixed(1)}倍`; cls = r>=1?'diff-up':'diff-down'; }
      if (kind==='pt') { const x = vb-va; d = `${x>=0?'+':''}${x.toFixed(1)}pt`; cls = x>=0?'diff-up':'diff-down'; }
      if (kind==='db') { const x = vb-va; d = `${x>=0?'+':''}${x.toFixed(1)}dB`; cls = x>=0?'diff-up':'diff-down'; }
    }
    box.append(el('div', cls, d));
  }
})();

// ---------- タイムライン
const S = D.series, N = D.bins, B = D.bin_sec;
const ROWS = [
  {key:'count', label:'コメント量', f:v=>`${v}件/${B}秒`, on:D.has.chat},
  {key:'accel', label:'加速度', f:v=>`${v>=0?'+':''}${v.toFixed(2)}`, on:D.has.chat},
  {key:'same', label:'同じコメント率', f:v=>`${(v*100).toFixed(0)}%`, on:D.has.chat},
  {key:'loud', label:'声の大きさ', f:v=>v==null?'—':`${v.toFixed(1)} dB`, on:D.has.audio},
  {key:'talk', label:'喋る量', f:v=>v==null?'—':`${(v*100).toFixed(0)}%`, on:D.has.audio},
  {key:'heat', label:'よく再生', f:v=>`${(v*100).toFixed(0)}`, on:D.has.heat},
  {key:'score', label:'盛り上がり', f:v=>`${v}`, on:true},
].filter(r => r.on && S[r.key]);

// 行ごとに「その配信の中での順位」を 0〜1 にする（色の明るさ）
for (const r of ROWS) {
  const vals = S[r.key].map(v => v==null ? null : v);
  const sorted = vals.filter(v => v!=null).slice().sort((a,b)=>a-b);
  const n = sorted.length;
  const rank = v => { let lo=0, hi=n; while(lo<hi){const m=(lo+hi)>>1; if(sorted[m]<v) lo=m+1; else hi=m;} return n>1? lo/(n-1) : 0; };
  r.norm = vals.map(v => v==null ? null : rank(v));
  r.min = n ? sorted[0] : 0; r.max = n ? sorted[n-1] : 1;
}

const STOPS = [[0,[27,31,42]],[0.45,[60,50,130]],[0.75,[200,50,110]],[0.92,[255,90,80]],[1,[255,215,110]]];
function cmap(x){
  for (let i=1;i<STOPS.length;i++){ if (x<=STOPS[i][0]){ const [a,ca]=STOPS[i-1],[b,cb]=STOPS[i]; const k=(x-a)/(b-a||1);
    return `rgb(${ca.map((c,j)=>Math.round(c+(cb[j]-c)*k)).join(',')})`; } }
  return `rgb(${STOPS[STOPS.length-1][1].join(',')})`;
}

let MODE = 'heat', V0 = 0, V1 = D.duration;
const cv = $('tl'), tip = $('tip');
const LABEL_W = 110, SEG_H = 24, ROW_H = 26, LINE_H = 54, AXIS_H = 22, GAP = 4;

function layout(){
  const rh = MODE==='heat' ? ROW_H : LINE_H;
  return {rh, H: SEG_H + GAP + ROWS.length*(rh+GAP) + AXIS_H};
}
function draw(hoverX){
  const W = cv.clientWidth, {rh, H} = layout();
  const dpr = window.devicePixelRatio || 1;
  cv.style.height = H + 'px'; cv.width = W*dpr; cv.height = H*dpr;
  const c = cv.getContext('2d'); c.setTransform(dpr,0,0,dpr,0,0); c.clearRect(0,0,W,H);
  const PW = W - LABEL_W;
  const X = t => LABEL_W + (t - V0) / (V1 - V0) * PW;
  c.font = '12px "Yu Gothic UI","Meiryo",sans-serif'; c.textBaseline = 'middle';

  // パート・試合の帯
  c.fillStyle = '#9aa3b2'; c.fillText('パート／試合', 4, SEG_H/2);
  c.fillStyle = '#20242d'; c.fillRect(LABEL_W, 0, PW, SEG_H);
  for (const p of D.phases) {
    c.fillStyle = p.key==='practice' ? '#2bb3a355' : '#8b6cf033';
    const x0 = Math.max(LABEL_W, X(p.start)), x1 = Math.min(W, X(p.end));
    if (x1 > x0) c.fillRect(x0, 0, x1-x0, SEG_H);
  }
  D.matches.forEach((m, i) => {
    const x0 = Math.max(LABEL_W, X(m.start)), x1 = Math.min(W, X(m.end));
    if (x1 <= x0) return;
    c.fillStyle = i%2 ? '#8b6cf099' : '#a48cffcc';
    c.fillRect(x0, 3, Math.max(1, x1-x0-1), SEG_H-6);
    if (x1 - x0 > 22) { c.fillStyle = '#fff'; c.textAlign='center'; c.fillText(String(m.no), (x0+x1)/2, SEG_H/2); c.textAlign='left'; }
  });

  // 指標の行
  const b0 = Math.max(0, Math.floor(V0 / B)), b1 = Math.min(N-1, Math.ceil(V1 / B));
  ROWS.forEach((r, ri) => {
    const y = SEG_H + GAP + ri*(rh+GAP);
    c.fillStyle = '#9aa3b2'; c.fillText(r.label, 4, y + rh/2);
    c.fillStyle = '#1b1f2a'; c.fillRect(LABEL_W, y, PW, rh);
    if (MODE === 'heat') {
      for (let i=b0; i<=b1; i++) {
        const v = r.norm[i]; if (v==null) continue;
        const x0 = X(i*B), x1 = X((i+1)*B);
        c.fillStyle = cmap(v); c.fillRect(Math.floor(x0), y, Math.max(1, Math.ceil(x1)-Math.floor(x0)), rh);
      }
    } else {
      // 表示範囲の中で最小〜最大
      let lo=Infinity, hi=-Infinity;
      for (let i=b0;i<=b1;i++){ const v=S[r.key][i]; if(v==null) continue; lo=Math.min(lo,v); hi=Math.max(hi,v); }
      if (!isFinite(lo)) return;
      if (hi===lo) hi = lo + 1;
      c.strokeStyle = r.key==='score' ? '#ff4d6d' : (r.key==='loud'||r.key==='talk') ? '#2bb3a3' : '#7cc4ff';
      c.lineWidth = 1.5; c.beginPath(); let started=false;
      for (let i=b0;i<=b1;i++){ const v=S[r.key][i]; if(v==null){started=false;continue;}
        const px = X((i+0.5)*B), py = y + rh - 3 - (v-lo)/(hi-lo)*(rh-6);
        if(!started){c.moveTo(px,py);started=true;} else c.lineTo(px,py); }
      c.stroke();
    }
  });

  // 見どころの印（スコア行の上）
  c.fillStyle = '#ffd166';
  for (const h of D.highlights) {
    if (h.peak < V0 || h.peak > V1) continue;
    const x = X(h.peak); c.beginPath(); c.moveTo(x-4, SEG_H); c.lineTo(x+4, SEG_H); c.lineTo(x, SEG_H+6); c.fill();
  }

  // 時間の目盛り
  const ay = H - AXIS_H/2;
  const span = V1 - V0, steps = [60,120,300,600,900,1800,3600,7200];
  const step = steps.find(s => span / s <= Math.max(4, PW/90)) || 7200;
  c.fillStyle = '#9aa3b2'; c.textAlign = 'center';
  for (let t = Math.ceil(V0/step)*step; t <= V1; t += step) {
    const x = X(t); c.fillRect(x, H-AXIS_H, 1, 4);
    const lab = fmt(t).replace(/^0:/,''); const lw = c.measureText(lab).width/2;
    c.fillText(lab, Math.min(Math.max(x, LABEL_W+lw), W-lw-1), ay+2);
  }
  c.textAlign = 'left';

  if (hoverX != null && hoverX >= LABEL_W) {
    c.fillStyle = '#ffffffaa'; c.fillRect(hoverX, 0, 1, H - AXIS_H);
  }
}

function tAt(x){ return V0 + (x - LABEL_W) / (cv.clientWidth - LABEL_W) * (V1 - V0); }
cv.addEventListener('mousemove', e => {
  const r = cv.getBoundingClientRect(), x = e.clientX - r.left;
  if (x < LABEL_W) { tip.style.display='none'; draw(); return; }
  draw(x);
  const t = tAt(x), i = Math.max(0, Math.min(N-1, Math.floor(t / B)));
  const m = D.matches.find(m => m.start <= t && t < m.end);
  const p = D.phases.find(p => p.start <= t && t < p.end);
  tip.textContent = '';
  tip.append(el('div', null, `${fmt(i*B)}〜${fmt((i+1)*B)}${p ? '　' + p.name : ''}${m ? '　試合' + m.no : ''}`));
  for (const row of ROWS) tip.append(el('div', null, `${row.label}：${row.f(S[row.key][i])}`));
  tip.style.display = 'block';
  const tw = tip.offsetWidth;
  tip.style.left = Math.min(x + 14, cv.clientWidth - tw - 4) + 'px';
  tip.style.top = (e.clientY - r.top + 14) + 'px';
});
cv.addEventListener('mouseleave', () => { tip.style.display='none'; draw(); });
cv.addEventListener('click', e => {
  const r = cv.getBoundingClientRect(), x = e.clientX - r.left;
  if (x < LABEL_W) return;
  window.open(yt(tAt(x) - D.lead), '_blank');
});
window.addEventListener('resize', () => draw());

$('mHeat').onclick = () => { MODE='heat'; $('mHeat').classList.add('on'); $('mLine').classList.remove('on'); draw(); };
$('mLine').onclick = () => { MODE='line'; $('mLine').classList.add('on'); $('mHeat').classList.remove('on'); draw(); };

// 表示範囲
const zoom = $('zoom');
const opts = [['all', '全体', 0, D.duration]];
for (const p of D.phases) opts.push([p.key, p.name, p.start, p.end]);
for (const m of D.matches) opts.push(['m'+m.no, `試合${m.no}（${fmt(m.start)}〜）`, Math.max(0, m.start-30), Math.min(D.duration, m.end+30)]);
for (const [v, label] of opts) { const o = el('option', null, label); o.value = v; zoom.append(o); }
function setZoom(v){ const o = opts.find(x => x[0]===v) || opts[0]; zoom.value = o[0]; V0 = o[2]; V1 = Math.max(o[3], o[2] + B); draw(); }
zoom.onchange = () => setZoom(zoom.value);

// 凡例
{
  const lg = $('legend');
  const g = el('span'); g.append('低い'); const gr = el('span','grad');
  gr.style.background = `linear-gradient(90deg, ${[0,.45,.75,.92,1].map(cmap).join(',')})`; g.append(gr, '高い');
  lg.append(g);
  if (D.phases.length) {
    const a = el('span'); const s1 = el('span','sw'); s1.style.background='#2bb3a3'; a.append(s1, '序盤（雑談・練習）');
    const b = el('span'); const s2 = el('span','sw'); s2.style.background='#a48cff'; b.append(s2, '試合（数字は試合番号）');
    lg.append(a, b);
  }
  const c2 = el('span'); const s3 = el('span','sw'); s3.style.background='#ffd166'; c2.append(s3, '見どころ候補'); lg.append(c2);
}

// ---------- 試合ごと
(function renderMatches(){
  if (!D.matches.length) { $('matchCard').style.display='none'; return; }
  $('matchTitle').textContent = `試合ごと（${D.matches.length}試合）`;
  const cols = [
    ['cpm', v => v==null?'—':v],
    ['same', v => v==null?'—':v+'%'],
    ['loud', v => v==null?'—':v+' dB'],
    ['talk', v => v==null?'—':v+'%'],
    ['score_max', v => v],
  ];
  const mx = {};
  for (const [k] of cols) {
    const vs = D.matches.map(m => m.stats && m.stats[k]).filter(v => v!=null);
    mx[k] = vs.length ? [Math.min(...vs), Math.max(...vs)] : [0,1];
  }
  const tb = $('mt');
  for (const m of D.matches) {
    const s = m.stats || {};
    const tr = el('tr','mrow');
    tr.append(el('td', null, '試合' + m.no));
    const td = el('td'); td.append(link(m.start)); tr.append(td);
    tr.append(el('td', null, fmtDur(m.end - m.start)));
    for (const [k, f] of cols) {
      const v = s[k]; const cell = el('td','bar', f(v));
      if (v != null) { const [lo,hi] = mx[k]; const i = el('i'); i.style.width = (hi>lo ? 15 + 85*(v-lo)/(hi-lo) : 50) + '%'; cell.append(i); }
      tr.append(cell);
    }
    const hb = el('td');
    if (s.best != null) { hb.append(link(s.best)); hb.append(el('span','sub',`　${s.highlights}か所`)); } else hb.append(el('span','sub','—'));
    tr.append(hb);
    tr.addEventListener('click', e => { if (e.target.tagName==='A') return; setZoom('m'+m.no); $('tl').scrollIntoView({behavior:'smooth', block:'center'}); });
    tb.append(tr);
  }
})();

// ---------- 見どころ候補
let SORT = 'score', FILTER = 'all';
const seen = new Set();
function place(h){
  if (h.match) return ['b-ranked', '試合' + h.match];
  if (h.phase === 'practice') return ['b-practice', '序盤'];
  if (h.phase === 'ranked') return ['b-ranked', '後半'];
  return null;
}
function renderHL(){
  const tb = $('hl'); tb.textContent = '';
  let hs = D.highlights.slice();
  if (FILTER !== 'all') hs = hs.filter(h => FILTER==='practice' ? h.phase==='practice' : h.phase==='ranked');
  hs.sort((a,b) => SORT==='time' ? a.start-b.start : b.score-a.score);
  if (!hs.length) { const tr = el('tr'); const td = el('td','sub','該当する候補はありません'); td.colSpan = 5; tr.append(td); tb.append(tr); }
  for (const h of hs) {
    const tr = el('tr', seen.has(h.start) ? 'seen' : '');
    tr.append(el('td','sub', h.rank));
    const t = el('td'); const a = link(h.start); a.addEventListener('click', () => { seen.add(h.start); tr.classList.add('seen'); });
    t.append(a, el('div','sub', '〜 ' + fmt(h.end))); tr.append(t);
    const pl = el('td'); const p = place(h); if (p) pl.append(el('span','badge ' + p[0], p[1])); tr.append(pl);
    tr.append(el('td','score', h.score));
    const r = el('td');
    h.reasons.forEach((x, i) => { if (i) r.append(el('br')); r.append(x); });
    const ch = el('div','chips2'); for (const [k, n] of h.top) ch.append(el('span', null, `${k} ×${n}`)); r.append(ch);
    tr.append(r);
    tb.append(tr);
  }
  $('sScore').classList.toggle('on', SORT==='score'); $('sTime').classList.toggle('on', SORT==='time');
  document.querySelectorAll('[data-f]').forEach(b => b.classList.toggle('on', b.dataset.f===FILTER));
}
if (D.phases.length > 1) {
  for (const [f, label] of [['all','すべて'],['practice','序盤'],['ranked','後半']]) {
    const b = el('button','chip',label); b.dataset.f = f; b.onclick = () => { FILTER = f; renderHL(); }; $('filters').append(b, ' ');
  }
}
$('sScore').onclick = () => { SORT='score'; renderHL(); };
$('sTime').onclick = () => { SORT='time'; renderHL(); };

renderHL();
setZoom('all');
</script></body></html>
"""
