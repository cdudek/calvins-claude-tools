// The web page as plain data in, one HTML string out: no engine, file, process or clock access. The page draws itself
// in the browser from an inline JSON block with textContent, so no value is ever put into markup. The only text that
// reaches the HTML is that block, with `<`, `>` and `&` written as \u escapes, and the count in the title.
import type { SessionRecord, Snapshot } from '../types'
import { clean } from './format'
import { repoPrs } from './git'
import { isLive, repoLabel } from './rank'
import { ASK_KIND, ASK_STATUS, CHECKS_WORDS, DETACHED, MERGE_WORDS, REASON_WORDS, REVIEW_WORDS, UNTITLED } from './words'

export const BOARD_FILE = 'board.html'
export const BOARD_PATH_TEXT = '~/.claude/agent-tracker/board.html'
export const BOARD_RELOAD_MS = 5000
export const BOARD_WRITE_MS = 10_000

// "You should know" and "Decided without you": a field another part of the mod adds to a session record. Read when
// present, shown as nothing when absent.
export type Note = { id: string; kind: 'know' | 'decided'; text: string; at: number; seen: boolean }

// The files of one change folder the pages read; each is the file's text, absent when the folder has no such file.
export type ChangeFiles = { repoPath: string; folder: string; milestone: string; facts?: string; validation?: string; questions?: string; findings?: string; done?: string }

const SESSIONS_MAX = 300
const ASKS_KEPT = 30
const DAYS = 7 * 24 * 3600 * 1000
const TEXT = 300

type Row = Record<string, unknown>
const cells = (line: string) => line.split('|').map(c => c.trim())

export const notesOf = (r: SessionRecord): Note[] => {
  const list = (r as { notes?: unknown }).notes
  if (!Array.isArray(list)) return []
  return (list as Row[])
    .filter(n => n !== null && typeof n === 'object' && (n.kind === 'know' || n.kind === 'decided') && typeof n.at === 'number')
    .map((n, i) => ({ id: clean(n.id ?? i, 80), kind: n.kind as Note['kind'], text: clean(n.text, TEXT), at: n.at as number, seen: n.seen === true }))
}

// milestone.md, the Features table with its PR or commit cell (parseMilestone keeps no cell but name and state).
const featureRows = (text: string) =>
  text
    .split('\n')
    .map(cells)
    .filter(c => c.length >= 6 && /^\d+$/.test(c[1]!))
    .map(c => ({ n: Number(c[1]), name: clean(c[3], TEXT), ref: clean(c[4], 80), state: clean(c[5], TEXT) }))

const front = (text: string, key: string) => new RegExp(`^${key}:\\s*(.+?)\\s*$`, 'm').exec(/^---\n([\s\S]*?)\n---/.exec(text)?.[1] ?? '')?.[1]

type Fact = { id: string; feature: number | null; text: string | null; verdict: string | null; check: string | null }

// facts.md gives each fact's words, done.json its feature and check, validation.md its verdict (the last cell of its row).
const factsOf = (c: ChangeFiles): Fact[] => {
  const words = new Map<string, string>()
  for (const m of (c.facts ?? '').matchAll(/^- \[[ x]\] \*\*(F\d+)\*\*\s*(?:\([^)]*\))?\s*(.+)$/gm)) words.set(m[1]!, clean(m[2], TEXT))
  const verdicts = new Map<string, string>()
  for (const line of (c.validation ?? '').split('\n')) {
    const cs = cells(line)
    if (cs.length >= 4 && /^F\d+$/.test(cs[1]!)) verdicts.set(cs[1]!, clean(cs[cs.length - 2], 60))
  }
  let listed: { id: string; feature: number | null; check: string | null }[] = []
  try {
    const parsed = JSON.parse(c.done ?? '{}') as { facts?: Row[] }
    listed = (parsed.facts ?? []).filter(f => typeof f?.id === 'string').map(f => ({ id: String(f.id), feature: typeof f.feature === 'number' ? f.feature : null, check: typeof f.check === 'string' ? clean(f.check, TEXT) : null }))
  } catch {
    // a torn or missing done.json: the facts come from facts.md alone
  }
  const ids = listed.length > 0 ? listed : [...words.keys()].map(id => ({ id, feature: null, check: null }))
  return ids.map(f => ({ ...f, text: words.get(f.id) ?? null, verdict: verdicts.get(f.id) ?? null }))
}

// questions.md: `- **Q7 (F4, step 3): the question?** ... **Default taken:** ... **To change:** ...`
const questionsOf = (text: string | undefined) =>
  [...(text ?? '').matchAll(/^- \*\*(Q\d+)\b([^*]*)\*\*\s*(.*)$/gm)].map(m => ({
    id: m[1]!,
    text: clean(m[2]!.replace(/^[\s:]+/, '').replace(/^\([^)]*\):?\s*/, ''), TEXT),
    taken: clean(/\*\*Default taken:\*\*\s*(.*?)(?:\s*\*\*To change:\*\*|$)/.exec(m[3]!)?.[1], TEXT),
  }))

// findings.md: `- [ ] **S1 title** ...` open, `- [x]` fixed; items under "## Advisory" do not block.
const findingsOf = (text: string | undefined) => {
  let advisory = false
  const items: { open: boolean; text: string }[] = []
  for (const line of (text ?? '').split('\n')) {
    if (line.startsWith('## ')) advisory = /^##\s+Advisory/i.test(line)
    const m = /^- \[([ x])\]\s*(.+)$/.exec(line)
    if (m !== null && !advisory) items.push({ open: m[1] === ' ', text: clean(m[2]!.replace(/\*\*/g, ''), TEXT) })
  }
  return items
}

const milestoneOf = (c: ChangeFiles) => {
  const slug = clean(front(c.milestone, 'milestone'), 200)
  const branch = clean(front(c.milestone, 'branch'), 200)
  if (slug === '' || branch === '') return null
  return {
    repoPath: c.repoPath,
    slug,
    branch,
    change: clean(c.folder, 200),
    sentence: clean(/^>\s*(.+)$/m.exec(c.milestone)?.[1], TEXT),
    features: featureRows(c.milestone),
    facts: factsOf(c),
    questions: questionsOf(c.questions),
    findings: findingsOf(c.findings),
  }
}

const sessionOf = (r: SessionRecord, snap: Snapshot, now: number) => {
  const prs = r.repo ? repoPrs(snap.sessions, r.repo.path, now) : null
  const onBranch = prs !== null && prs.ghOk && r.branch !== null ? prs.prs.find(p => p.branch === r.branch) : undefined
  return {
    id: r.sessionId,
    repo: repoLabel(r),
    repoPath: r.repo?.path ?? null,
    title: r.title ?? UNTITLED,
    state: r.state,
    reason: r.reason,
    unknownValue: r.unknownValue,
    live: isLive(r),
    branch: r.branch ?? (r.repo ? DETACHED : null),
    since: r.engine.since,
    startedAt: r.startedAt,
    lastActivityAt: r.lastActivityAt,
    endedAt: r.endedAt,
    source: r.source,
    usage: { in: r.usage.tokensIn, out: r.usage.tokensOut, errors: r.usage.toolErrors, retries: r.usage.retries },
    goalSince: r.runs.goalSince,
    subagents: r.runs.subagents.map(a => ({ name: a.name, status: a.status })),
    background: r.runs.background.map(b => ({ name: b.name, since: b.since })),
    asks: r.asks.slice(-ASKS_KEPT).map(a => ({ n: a.n, kind: a.kind, status: a.status, at: a.at, text: clean(a.text, TEXT) })),
    asksTotal: r.asks.length,
    milestone: r.milestone,
    pr: onBranch ? { number: onBranch.number, url: onBranch.url, checks: onBranch.checks } : null,
    notes: notesOf(r),
    resume: r.state === 'ended' ? `cd '${r.cwd.replace(/'/g, "'\\''")}' && claude --resume ${r.sessionId}` : null,
  }
}

export type BoardData = ReturnType<typeof boardData>

// Everything the pages need. A session older than a week with nothing live about it is left out, so the page stays small.
export const boardData = (snap: Snapshot, changes: ChangeFiles[], now: number) => {
  const recent = snap.sessions
    .filter(r => isLive(r) || Math.max(r.lastActivityAt, r.endedAt ?? 0) >= now - DAYS)
    .sort((a, b) => Math.max(b.lastActivityAt, b.endedAt ?? 0) - Math.max(a.lastActivityAt, a.endedAt ?? 0))
    .slice(0, SESSIONS_MAX)
  const paths = [...new Set(recent.flatMap(r => (r.repo ? [r.repo.path] : [])))]
  const repos = paths.map(path => {
    const prs = repoPrs(snap.sessions, path, now)
    const scans = snap.sessions.filter(r => r.repo?.path === path && r.scan !== null).map(r => r.scan!)
    const trees = scans.reduce<(typeof scans)[number] | null>((best, s) => (best === null || s.at > best.at ? s : best), null)?.worktrees ?? []
    return {
      path,
      label: repoLabel(recent.find(r => r.repo?.path === path)!),
      prs: prs && { at: prs.at, ghOk: prs.ghOk, github: prs.github, hasLive: prs.hasLive, list: prs.prs },
      worktrees: trees,
    }
  })
  return {
    v: 1 as const,
    builtAt: now,
    agentsOk: snap.agentsOk,
    stale: snap.at !== 0 && snap.failedReads >= 2,
    loading: snap.at === 0,
    sessions: recent.map(r => sessionOf(r, snap, now)),
    repos,
    milestones: changes.flatMap(c => {
      const m = paths.includes(c.repoPath) ? milestoneOf(c) : null
      return m === null ? [] : [m]
    }),
    words: { reason: REASON_WORDS, askKind: ASK_KIND, askStatus: ASK_STATUS, checks: CHECKS_WORDS, review: REVIEW_WORDS, merge: MERGE_WORDS },
  }
}

// The count in the tab title: sessions that need you now.
export const needsCount = (d: BoardData) => d.sessions.filter(s => s.live && s.state === 'needs-you').length
export const titleOf = (n: number) => (n > 0 ? `(${n}) Agent tracker` : 'Agent tracker')

// A JSON block inside a <script>: nothing in it can close the tag or start a comment.
export const inlineJson = (value: unknown) =>
  JSON.stringify(value).replace(/[<>&\u2028\u2029]/g, c => `\\u${c.charCodeAt(0).toString(16).padStart(4, '0')}`)

// The look is the owner's mockups: a dark page, monospace, one colour class per meaning (r y g c m d b).
const CSS = String.raw`
:root{--bg:#0d1117;--card:#0d1117;--line:#243039;--tfg:#c9d1d9;--dim:#6e7681;--red:#ff7b72;--yel:#e3b341;--grn:#56d364;--cyn:#79c0ff;--mag:#d2a8ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tfg);padding:20px 24px 60px;font:13px/1.5 ui-monospace,"SF Mono",Menlo,Consolas,monospace}
#app{max-width:980px;margin:0 auto}
.l{white-space:pre-wrap;word-break:break-word;min-height:1.5em}
.r{color:var(--red)}.y{color:var(--yel)}.g{color:var(--grn)}.c{color:var(--cyn)}.m{color:var(--mag)}.d{color:var(--dim)}.b{font-weight:700;color:#fff}.s{text-decoration:line-through;color:var(--dim)}
a{color:inherit;text-decoration:none}a:hover,a:focus{background:#161b22;outline:1px solid var(--line)}
button{font:inherit;background:transparent;color:var(--dim);border:1px solid var(--line);border-radius:4px;padding:1px 8px;cursor:pointer}
button:hover{color:#fff}
.compact .sub{display:none}
.bar{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}
.rule{border-top:1px solid var(--line);margin:6px 0}
`

// The page's own script: reads the JSON block and draws the route in location.hash with textContent only. No innerHTML.
const SCRIPT = String.raw`
(function(){
var D=JSON.parse(document.getElementById('data').textContent),NOW=D.builtAt,W=D.words,app=document.getElementById('app');
var enc=encodeURIComponent;
function node(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e}
function dur(ms){var m=Math.floor(Math.max(0,ms)/60000);if(m<1)return '<1m';if(m<60)return m+'m';if(m<1440)return m%60===0?(m/60)+'h':Math.floor(m/60)+'h '+(m%60)+'m';return Math.floor(m/1440)+'d'}
function two(n){return (n<10?'0':'')+n}
function midnight(){var t=new Date(NOW);t.setHours(0,0,0,0);return t.getTime()}
function clock(ms){var d=new Date(ms);if(ms>=midnight())return two(d.getHours())+':'+two(d.getMinutes());if(NOW-ms<6048e5)return ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][d.getDay()]+'  ';return d.toLocaleDateString(undefined,{day:'numeric',month:'short'})}
function tok(n){return n<1000?String(n):n<1e6?Math.round(n/1000)+'k':(n/1e6).toFixed(1).replace(/\.0$/,'')+'M'}
function cut(s,n){s=String(s).replace(/\s+/g,' ').trim();return s.length>n?s.slice(0,n-1)+'…':s}
function plural(n,a,b){return n+' '+(n===1?a:b)}
var H={home:'#/',repo:function(l){return '#/repo/'+enc(l)},ms:function(l,s){return '#/repo/'+enc(l)+'/milestone/'+enc(s)},ft:function(l,s,n){return '#/repo/'+enc(l)+'/milestone/'+enc(s)+'/feature/'+n},ses:function(i){return '#/session/'+enc(i)},note:function(i,n){return '#/session/'+enc(i)+'/note/'+enc(n)}};
// A part is a string, [class,text] or [class,text,href].
function line(cls,parts){var d=node('div','l'+(cls?' '+cls:''));parts.forEach(function(p){if(p==null||p===false)return;if(typeof p==='string'){d.appendChild(document.createTextNode(p));return}var h=p[2],a=h?node('a',p[0],p[1]):node('span',p[0],p[1]);if(h){if(h.charAt(0)==='#'){a.href=h}else if(h.indexOf('https://')===0){a.href=h;a.target='_blank';a.rel='noopener noreferrer'}}d.appendChild(a)});return d}
function L(){return line('',[].slice.call(arguments))}
function SUB(){return line('sub',[].slice.call(arguments))}
function head(label,cls,extra){return L([cls||'b',label],extra?'  ':null,extra?['d',extra]:null)}
function rule(){return node('div','rule')}
function bar(done,total,n){n=n||6;var f=total>0?Math.round(done/total*n):0;return [['g',new Array(f+1).join('▓')],['d',new Array(n-f+1).join('░')]]}
function glyph(s){return s.state==='needs-you'?['r','●']:s.state==='running'?['y','◐']:s.state==='done'?['g','✓']:['d','○']}
function isComplete(x){return /^(done|merged)\b/.test(x)}
function fglyph(x){return isComplete(x)?['g','✓']:/^building\b/.test(x)?['y','◐']:/^blocked\b/.test(x)?['r','✗']:['d','○']}
function verdictCls(v){return v==null?'d':/^met/.test(v)?'g':/^partial/.test(v)?'y':'r'}
function sesName(s){return s.repo+'/'+(s.branch||s.title)}
function sessions(f){return D.sessions.filter(f)}
function repoOf(l){return D.repos.filter(function(r){return r.label===l})[0]||null}
function sesById(i){return D.sessions.filter(function(s){return s.id===i})[0]||null}
function msOf(l,slug){var r=repoOf(l);return r?D.milestones.filter(function(m){return m.repoPath===r.path&&m.slug===slug})[0]||null:null}
function prOf(r,branch){return r&&r.prs&&r.prs.ghOk?r.prs.list.filter(function(p){return p.branch===branch})[0]||null:null}
function lastAsk(s){return s.asks.length?s.asks[s.asks.length-1].text:null}
function allNotes(){var out=[];D.sessions.forEach(function(s){s.notes.forEach(function(n){out.push({s:s,n:n})})});return out}
function crumbs(list){var parts=[];list.forEach(function(c,i){if(i>0)parts.push(' › ');parts.push(c[1]?['d',c[0],c[1]]:['b',c[0]])});return line('',parts)}
function prsTotals(){var open=0,fail=0,conf=0;D.repos.forEach(function(r){if(r.prs&&r.prs.ghOk){r.prs.list.forEach(function(p){open++;if(p.checks==='failing')fail++;if(p.mergeable==='conflicts')conf++})}});return {open:open,fail:fail,conf:conf}}

function top(el,trail,right){
  var b=node('div','bar');var left=node('div');left.appendChild(trail);b.appendChild(left);
  var r=node('div');r.appendChild(right||document.createTextNode(''));b.appendChild(r);el.appendChild(b)}
function age(){var ms=Date.now()-NOW;return ms>20000?line('',[['y','No session is updating this page. Last build '+dur(ms)+' ago.']]):null}
function toolbar(){
  var w=node('span');var c=node('button',null,document.body.classList.contains('compact')?'Details':'Compact');
  c.type='button';c.addEventListener('click',function(){var on=!document.body.classList.contains('compact');document.body.classList.toggle('compact',on);try{localStorage.setItem('agent-tracker-compact',on?'1':'0')}catch(e){}c.textContent=on?'Details':'Compact'});
  w.appendChild(c);return w}
function page(trail,body){app.textContent='';top(app,trail,toolbar());var a=age();if(a)app.appendChild(a);app.appendChild(rule());body.forEach(function(n){app.appendChild(n)})}

function notesBlock(kind,title,cls,mark,list,out,withRepo){
  var mine=list.filter(function(x){return x.n.kind===kind});if(!mine.length)return;
  var unseen=mine.filter(function(x){return !x.n.seen}),seen=mine.filter(function(x){return x.n.seen});
  unseen.sort(function(a,b){return b.n.at-a.n.at});seen.sort(function(a,b){return b.n.at-a.n.at});
  out.push(L([cls,title],'  ',unseen.length?[cls,unseen.length+' new']:['d','none new']));
  unseen.forEach(function(x){out.push(L([cls,mark],' ',[null,withRepo?x.s.repo+'/'+x.s.title:x.s.title,H.note(x.s.id,x.n.id)],'  ',['d',clock(x.n.at)]));out.push(SUB('   ',cut(x.n.text,110)))});
  seen.forEach(function(x){out.push(L(['d','· '],['d',x.s.repo+'  '+clock(x.n.at)+'  seen',H.note(x.s.id,x.n.id)]))});
}

function home(){
  var live=sessions(function(s){return s.live}),need=live.filter(function(s){return s.state==='needs-you'}),run=live.filter(function(s){return s.state==='running'});
  var out=[];
  out.push(L(['r','NEEDS YOU']));
  if(!need.length)out.push(L(['d','  Nothing needs you.']));
  need.sort(function(a,b){return (a.since===null)-(b.since===null)||(a.since||0)-(b.since||0)}).forEach(function(s){
    out.push(L(glyph(s),' ',[null,sesName(s),H.ses(s.id)],'  ',['r',W.reason[s.reason||'waiting']],s.since===null?null:['d','  '+dur(NOW-s.since)]));
    var q=lastAsk(s);if(q)out.push(SUB('   ',['d','“'+cut(q,100)+'”']))});
  var notes=allNotes();if(notes.length){out.push(rule());notesBlock('know','YOU SHOULD KNOW','c','!',notes,out,true);notesBlock('decided','DECIDED WITHOUT YOU','m','◆',notes,out,true)}
  out.push(rule());
  out.push(L(['y','RUNNING'],'  ',['y','◐ '+plural(run.length,'session','sessions')]));
  run.sort(function(a,b){return (a.since||0)-(b.since||0)}).forEach(function(s){
    var m=s.milestone,done=m?m.features.filter(function(f){return isComplete(f.state)}).length:0;
    out.push(L(glyph(s),' ',[null,sesName(s),H.ses(s.id)],m&&m.features.length?'  '+done+'/'+m.features.length+' ':null,m&&m.features.length?bar(done,m.features.length)[0]:null,m&&m.features.length?bar(done,m.features.length)[1]:null,s.goalSince?['c','  goal '+dur(NOW-s.goalSince)]:null,s.since===null?null:['d','  '+dur(NOW-s.since)],s.usage.retries>0?['y','  '+plural(s.usage.retries,'retry','retries')]:null))});
  out.push(rule());
  var done=live.filter(function(s){return s.state==='done'}).length,p=prsTotals(),today=0;
  D.sessions.forEach(function(s){if(s.lastActivityAt>=midnight())today+=s.usage.in+s.usage.out});
  out.push(L(['g','✓'],' done '+done,p.open?'   PRs '+p.open+' open':null,p.fail?['d',' · ']:null,p.fail?['r',p.fail+' failing']:null,p.conf?['d',' · ']:null,p.conf?['y',p.conf+' conflicts']:null));
  out.push(SUB(['d','tokens today '+tok(today)]));
  var ended=sessions(function(s){return s.state==='ended'&&s.endedAt>=midnight()});
  if(ended.length){out.push(rule());out.push(L(['d','ENDED TODAY']));ended.slice(0,5).forEach(function(s){out.push(L(['d','○ '],[null,sesName(s),H.ses(s.id)],['d','  ended '+dur(NOW-s.endedAt)+' ago']))})}
  out.push(rule());
  out.push(L(['b','REPOS']));
  if(!D.repos.length)out.push(L(['d','  No repos yet.']));
  D.repos.forEach(function(r){var n=live.filter(function(s){return s.repoPath===r.path&&s.state==='needs-you'}).length;out.push(L('  ',['c',r.label,H.repo(r.label)],n?['r','  '+n+' needs you']:null,r.prs&&r.prs.ghOk&&r.prs.list.length?['d','  '+plural(r.prs.list.length,'PR','PRs')]:null))});
  var t=L(['b','Agent tracker'],'   ',['d',live.length+' live · '],need.length?['r',need.length+' need you']:['d','none need you']);
  var s2=D.loading?L(['d','Reading sessions…']):D.stale?L(['y','Session list unavailable. Showing what was last read.']):null;
  if(s2)out.unshift(s2);
  page(t,out);
}

function repoPage(label){
  var r=repoOf(label);if(!r)return missing('No repo named '+label+' has had a session.');
  var ss=sessions(function(s){return s.repoPath===r.path}),out=[],need=ss.filter(function(s){return s.live&&s.state==='needs-you'}).length;
  var ms=D.milestones.filter(function(m){return m.repoPath===r.path});
  if(ms.length){out.push(L(['b','MILESTONES']));ms.forEach(function(m){
    var met=m.facts.filter(function(f){return /^met/.test(f.verdict||'')}).length,fd=m.features.filter(function(f){return isComplete(f.state)}).length;
    var useFacts=m.facts.length>0,pr=prOf(r,m.branch),all=m.features.length>0&&fd===m.features.length;
    out.push(L(all?['g','✓']:['y','◐'],' ',[null,m.slug,H.ms(label,m.slug)],'  '+(useFacts?met+'/'+m.facts.length+' facts ':fd+'/'+m.features.length+' features '),bar(useFacts?met:fd,useFacts?m.facts.length:m.features.length)[0],bar(useFacts?met:fd,useFacts?m.facts.length:m.features.length)[1],pr?['c','  #'+pr.number,pr.url||undefined]:null,pr?(pr.checks==='pass'?['g',' ✓']:pr.checks==='failing'?['r',' ✗']:['y',' ◌']):null));
    out.push(SUB('   ',['d','changes/'+m.change+' · branch '+m.branch]))});out.push(rule())}
  var asks=[];ss.forEach(function(s){s.asks.forEach(function(a){asks.push({s:s,a:a})})});asks.sort(function(x,y){return y.a.at-x.a.at});
  var tasks=asks.filter(function(x){return x.a.kind==='task'}).length,qs=asks.filter(function(x){return x.a.kind==='question'}).length,open=asks.filter(function(x){return x.a.status!=='replied'}).length;
  out.push(L(['b','YOUR ASKS HERE'],'  ',['d',tasks+' tasks · '+qs+' questions · '+open+' open']));
  if(!asks.length)out.push(L(['d','  No asks yet.']));
  asks.slice(0,12).forEach(function(x){var st=x.a.status==='needs-you'?['r','●']:x.a.status==='in-progress'?['y','◐']:null;
    out.push(L(['d',clock(x.a.at)],' ',x.a.kind==='task'?['m','T']:x.a.kind==='question'?['d','Q']:['d','?'],' ',[x.a.kind==='question'?'d':null,cut(x.a.text,70),H.ses(x.s.id)],st?'  ':null,st))});
  out.push(rule());
  out.push(L(['b','SESSIONS']));
  ss.slice(0,12).forEach(function(s){out.push(L('  ',glyph(s),' ',[null,s.branch?s.branch+'  '+cut(s.title,40):cut(s.title,50),H.ses(s.id)],s.state==='ended'?['d','  ended '+dur(NOW-s.endedAt)+' ago']:s.since===null?null:['d','  '+dur(NOW-s.since)]))});
  if(r.worktrees.length){out.push(rule());out.push(L(['b','WORKTREES']));r.worktrees.forEach(function(w){var mine=ss.filter(function(s){return s.live&&w.branch&&s.branch===w.branch});out.push(L('  '+(w.path.split('/').pop()||w.path),['d','  '+(w.branch||'detached HEAD')],mine.length?['d','  ']:null,mine.length?glyph(mine[0]):null))})}
  out.push(rule());
  out.push(L(['b','PRs']));
  if(!r.prs)out.push(L(['d','  No scan yet.']));
  else if(r.prs.github===false)out.push(L(['d','  Not on GitHub.']));
  else if(!r.prs.ghOk)out.push(L(['d','  PRs not shown: gh is not installed or not signed in. Run gh auth login to see them.']));
  else{if(!r.prs.hasLive)out.push(SUB(['d','  PRs as of '+dur(NOW-r.prs.at)+' ago: no live session in this repo']));
    if(!r.prs.list.length)out.push(L(['d','  No open PRs.']));
    r.prs.list.slice().sort(function(a,b){return (b.checks==='failing')-(a.checks==='failing')||b.createdAt.localeCompare(a.createdAt)}).forEach(function(p){
      out.push(L('  ',['c','#'+p.number,p.url||undefined],'  '+cut(p.title,50)+'  ',p.checks==='pass'?['g',W.checks.pass]:p.checks==='failing'?['r',W.checks.failing]:['y',W.checks.running],['d',' · '+W.review[p.review]+' · '+W.merge[p.mergeable]]))})}
  page(crumbs([['Home',H.home],[label]]),[].concat(need?[L(['r',need+' needs you'])]:[],out));
}

function milestonePage(label,slug){
  var m=msOf(label,slug);if(!m)return missing('No milestone '+slug+' in '+label+'.');
  var r=repoOf(label),pr=prOf(r,m.branch),out=[];
  out.push(L(['d','changes/'+m.change+' · branch '+m.branch]));
  if(m.sentence)out.push(L(m.sentence));
  if(pr)out.push(L(['d','PR '],['c','#'+pr.number,pr.url||undefined],pr.checks==='pass'?['g','  checks pass']:pr.checks==='failing'?['r','  checks failing']:['y','  checks running']));
  out.push(rule());
  var fd=m.features.filter(function(f){return isComplete(f.state)}).length;
  out.push(L(['b','FEATURES'],'  ',['d',fd+'/'+m.features.length]));
  m.features.forEach(function(f){out.push(L(fglyph(f.state),' ',[null,f.n+' '+cut(f.name,70),H.ft(label,slug,f.n)],/^blocked/.test(f.state)?['r','  '+cut(f.state,60)]:/^done\s+\S+/.test(f.state)?['d','  '+f.state.replace(/^done\s+/,'')]:f.state==='merged'?['d','  merged']:null))});
  if(m.facts.length){var met=m.facts.filter(function(f){return /^met/.test(f.verdict||'')}).length;
    var fl=['b','FACTS'],parts=[fl,'  ',['d',met+'/'+m.facts.length+' met'],'  '];m.facts.forEach(function(f){parts.push([verdictCls(f.verdict),f.id],' ')});out.push(rule());out.push(L.apply(null,parts))}
  if(m.questions.length){out.push(rule());out.push(L(['b','QUESTIONS'],'  ',['y',m.questions.length+' logged']));m.questions.slice(0,8).forEach(function(q){out.push(L('  ',['y',q.id],' ',cut(q.text,80)));if(q.taken)out.push(SUB('     ',['d','default: '+cut(q.taken,100)]))})}
  var open=m.findings.filter(function(f){return f.open});
  {out.push(rule());out.push(L(['b','FINDINGS'],'  ',m.findings.length?[open.length?'r':'g',open.length+' open · '+(m.findings.length-open.length)+' fixed']:['d','none yet (review runs at close)']));open.slice(0,8).forEach(function(f){out.push(SUB('  ',['r','○ '],cut(f.text,100)))})}
  var ss=sessions(function(s){return s.milestone&&s.milestone.slug===slug&&s.repoPath===r.path});
  if(ss.length){out.push(rule());out.push(L(['b','SESSIONS']));ss.forEach(function(s){out.push(L('  ',glyph(s),' ',[null,cut(s.title,60),H.ses(s.id)]))})}
  page(crumbs([['Home',H.home],[label,H.repo(label)],[slug]]),out);
}

function featurePage(label,slug,n){
  var m=msOf(label,slug),f=m&&m.features.filter(function(x){return x.n===n})[0];if(!f)return missing('No feature '+n+' in '+slug+'.');
  var out=[],g=fglyph(f.state);
  out.push(L(g,' ',['b',f.n+' '+f.name],'   ',[g[0],f.state]));
  if(f.ref&&!/^<.*>$/.test(f.ref))out.push(L(['d','commit or PR '],f.ref));
  var facts=m.facts.filter(function(x){return x.feature===n});
  out.push(rule());
  if(facts.length){out.push(L(['b','FACTS'],'  ',facts.map(function(x){return x.id}).join(' ')));facts.forEach(function(x){out.push(L('  ',[verdictCls(x.verdict),x.id],'  ',x.verdict?[verdictCls(x.verdict),x.verdict]:['d','no verdict yet']));if(x.text)out.push(SUB('     ',cut(x.text,160)));if(x.check)out.push(SUB('     ',['d','check: '+cut(x.check,140)]))})}
  else out.push(L(['d','No facts are tied to this feature.']));
  page(crumbs([['Home',H.home],[label,H.repo(label)],[slug,H.ms(label,slug)],[f.n+' '+cut(f.name,40)]]),out);
}

function sessionPage(id){
  var s=sesById(id);if(!s)return missing('No session with this id.');
  var out=[],g=glyph(s);
  var state=s.state==='needs-you'?'needs you':s.state;
  out.push(L(['b',s.repo+' / '+s.title],'   ',[g[0],g[1]+' '+state+(s.since===null||s.state==='ended'?'':' '+dur(NOW-s.since))+(s.state==='needs-you'?' · '+W.reason[s.reason||'waiting']:'')+(s.state==='ended'?' '+dur(NOW-s.endedAt)+' ago':'')]));
  out.push(L(s.branch?['d','branch ']:null,s.branch,['d',(s.branch?'  ':'')+'started '],clock(s.startedAt),['d','  last activity '],dur(NOW-s.lastActivityAt)+' ago'));
  out.push(L(['d','tokens '],'in '+tok(s.usage.in)+' out '+tok(s.usage.out),['d','  tool errors '],String(s.usage.errors),['d','  retries '],[s.usage.retries>0?'y':null,String(s.usage.retries)]));
  if(s.goalSince&&s.live)out.push(L(['c','goal '+dur(NOW-s.goalSince)]));
  s.subagents.forEach(function(a){out.push(L(['d','subagent '],a.name+' · '+a.status))});
  s.background.forEach(function(b){out.push(L(['d','background '],b.name+' · '+dur(NOW-b.since)))});
  if(s.pr)out.push(L(['d','PR '],['c','#'+s.pr.number,s.pr.url||undefined],'  ',s.pr.checks==='pass'?['g',W.checks.pass]:s.pr.checks==='failing'?['r',W.checks.failing]:['y',W.checks.running]));
  if(s.milestone){var m=s.milestone,d=m.features.filter(function(f){return isComplete(f.state)}).length;out.push(rule());out.push(L(['b','MILESTONE'],'  ',['d',m.slug]));if(m.sentence)out.push(L(m.sentence));out.push(L(['d',d+' of '+m.features.length+' features complete ']),bar(d,m.features.length)[0],bar(d,m.features.length)[1]);m.features.forEach(function(f){out.push(L('  ',fglyph(f.state),' '+f.n+' '+cut(f.name,70)))})}
  if(s.notes.length){out.push(rule());notesBlock('know','YOU SHOULD KNOW','c','!',s.notes.map(function(n){return {s:s,n:n}}),out,false);notesBlock('decided','DECIDED WITHOUT YOU','m','◆',s.notes.map(function(n){return {s:s,n:n}}),out,false)}
  out.push(rule());
  out.push(L(['b','ASKS'],'  ',['d',s.asksTotal+' in all'+(s.source==='transcript'?' · not classified: this session ran without the tracker':'')]));
  if(!s.asks.length)out.push(L(['d','  No asks yet.']));
  s.asks.slice().reverse().forEach(function(a){out.push(L(['d',clock(a.at)],' ',a.kind==='task'?['m','T']:a.kind==='question'?['d','Q']:['d','?'],'  ',['d',W.askStatus[a.status]],'  ',cut(a.text,160)))});
  if(s.resume){out.push(rule());var row=L(['d','resume '],s.resume,'  ');var b=node('button',null,'Copy');b.type='button';b.addEventListener('click',function(){try{navigator.clipboard.writeText(s.resume).then(function(){b.textContent='Copied'})}catch(e){}});row.appendChild(b);out.push(row)}
  var tr=[['Home',H.home]];if(s.repoPath)tr.push([s.repo,H.repo(s.repo)]);tr.push([s.title]);
  page(crumbs(tr),out);
}

function notePage(id,nid){
  var s=sesById(id),n=s&&s.notes.filter(function(x){return x.id===nid})[0];if(!n)return missing('No such item.');
  var know=n.kind==='know',cls=know?'c':'m',out=[];
  out.push(L([cls,(know?'! ':'◆ ')+n.text]));
  out.push(L(['d','when '],clock(n.at),['d','   session '],[null,s.title,H.ses(s.id)],['d','   '+(n.seen?'seen':'unseen')]));
  out.push(rule());
  var text='Overruling "'+n.text+'"\nInstead: <your call>';
  out.push(L(['d','Copy this, to paste into that session:']));
  text.split('\n').forEach(function(t){out.push(L(['d','┆ '],t))});
  var row=L('');var b=node('button',null,'Copy overrule');b.type='button';b.addEventListener('click',function(){try{navigator.clipboard.writeText(text).then(function(){b.textContent='Copied'})}catch(e){}});row.appendChild(b);out.push(row);
  page(crumbs([['Home',H.home],[know?'you should know':'decided without you',H.home],[s.repo+'/'+s.title,H.ses(s.id)]]),out);
}

function missing(text){page(crumbs([['Home',H.home],['Not found']]),[L(['d',text])])}

function route(){
  var p;try{p=location.hash.replace(/^#\/?/,'').split('/').filter(Boolean).map(decodeURIComponent)}catch(e){p=[]}
  if(p[0]==='repo'&&p[2]==='milestone'&&p[4]==='feature')return featurePage(p[1],p[3],Number(p[5]));
  if(p[0]==='repo'&&p[2]==='milestone'&&p[3])return milestonePage(p[1],p[3]);
  if(p[0]==='repo'&&p[1])return repoPage(p[1]);
  if(p[0]==='session'&&p[2]==='note'&&p[3])return notePage(p[1],p[3]);
  if(p[0]==='session'&&p[1])return sessionPage(p[1]);
  home();
}
try{if(localStorage.getItem('agent-tracker-compact')==='1')document.body.classList.add('compact')}catch(e){}
route();
window.addEventListener('hashchange',function(){route();window.scrollTo(0,0)});
// Live: the mods rewrite this file every 10 seconds; reloading keeps the #/ route, and the scroll is put back.
try{var y=sessionStorage.getItem('agent-tracker-y');if(y!==null){window.scrollTo(0,Number(y));sessionStorage.removeItem('agent-tracker-y')}}catch(e){}
setTimeout(function(){try{sessionStorage.setItem('agent-tracker-y',String(window.scrollY))}catch(e){}location.reload()},__RELOAD__);
})();
`

export const boardHtml = (d: BoardData): string =>
  `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${titleOf(needsCount(d))}</title>
<style>${CSS}</style>
<body><div id="app"></div>
<script type="application/json" id="data">${inlineJson(d)}</script>
<script>${SCRIPT.replace('__RELOAD__', String(BOARD_RELOAD_MS))}</script>
</body></html>
`
