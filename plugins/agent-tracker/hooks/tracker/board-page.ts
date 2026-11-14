// The page itself: its stylesheet, its script and the one function that puts them round the data. The script runs in
// the browser (it reads the clock and the location there), so it lives beside the I/O files, not in core/, which
// reads no clock. The data and every value in it come from core/board-html.ts; no value is ever put into markup.
import { BOARD_RELOAD_MS, BOARD_STALE_MS, inlineJson, needsCount, titleOf } from './core/board-html'
import type { BoardData } from './core/board-html'

// Two looks in one page. The home page is the owner's web mockup (2026-11-14): proportional type, one colour per meaning. The
// drill-in pages (session, repo, milestone, feature, note) keep the dark terminal look of the owner's earlier mockups.
// `scope` puts a look's rules under its own `data-look` on <body>, so the two never touch.
const scope = (look: string, css: string) =>
  css.replace(/(^|\})\s*([^{}]+)\{/g, (_m, close: string, sel: string) => `${close}${sel.split(',').map(s => (s.trim() === 'body' ? `body[data-look=${look}]` : `body[data-look=${look}] ${s.trim()}`)).join(',')}{`)

const TERM_CSS = String.raw`
body{--bg:#0f1418;--card:#0d1117;--line:#243039;--tfg:#c9d1d9;--dim:#6e7681;--red:#ff7b72;--yel:#e3b341;--grn:#56d364;--cyn:#79c0ff;--mag:#d2a8ff;margin:0;background:var(--bg);color:var(--tfg);padding:20px 24px 60px;font:13px/1.5 ui-monospace,"SF Mono",Menlo,Consolas,monospace}
#app{max-width:980px;margin:0 auto;background:var(--card);border-radius:8px;padding:12px 14px;overflow-x:auto}
.l{white-space:pre-wrap;word-break:break-word;min-height:1.5em}
.r{color:var(--red)}.y{color:var(--yel)}.g{color:var(--grn)}.c{color:var(--cyn)}.m{color:var(--mag)}.d{color:var(--dim)}.b{font-weight:700;color:#fff}.s{text-decoration:line-through;color:var(--dim)}
a{color:inherit;text-decoration:none}
a:hover,a:focus{background:#161b22;outline:1px solid var(--line)}
button{font:inherit;background:transparent;color:var(--dim);border:1px solid var(--line);border-radius:4px;padding:1px 8px;cursor:pointer}
button:hover{color:#fff}
.bar{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}
.rule{border-top:1px solid var(--line);margin:6px 0}
.r2{display:flex;gap:14px;align-items:baseline}
`

const WEB_CSS = String.raw`
body{--bg:#0d1117;--panel:#151b23;--line:#2b3542;--fg:#e6edf3;--mut:#a3afbc;--red:#ff6b80;--yel:#ffc107;--blue:#b1b9f9;--pur:#af87ff;--grn:#56d364;margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--blue)}
a:focus-visible,button:focus-visible,summary:focus-visible{outline:2px solid var(--blue);outline-offset:3px}
.mut{color:var(--mut)}
.top{padding:22px 24px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:6px 24px;align-items:baseline}
.top h1{font-size:20px;margin:0}
.top p{margin:0;flex:1;min-width:240px}
.fresh{font-size:14px;color:var(--mut)}
.stale{margin:0;padding:10px 24px;color:var(--yel);border-bottom:1px solid var(--line);font-size:14.5px}
main{max-width:860px;margin:0 auto;padding:0 20px 64px}
h2{font-size:18px;margin:36px 0 14px}
ol.tasks{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:12px}
.row{--c:var(--yel);border:1px solid var(--line);border-left:4px solid var(--c);border-radius:8px;background:var(--panel);padding:14px 16px;display:grid;gap:6px}
.row.need{--c:var(--red)}
.row.lost{--c:var(--red);border-color:var(--red);border-left-width:4px}
.row.sup{--c:var(--pur)}
.ask{margin:0;font-size:16px;overflow-wrap:anywhere}
.line{display:flex;flex-wrap:wrap;gap:4px 14px;align-items:baseline;font-size:14px;color:var(--mut)}
.line b{color:var(--fg);font-weight:600}
.status{color:var(--c);font-weight:600}
.foot{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;font-size:14px}
.grow{flex:1}
button{font:inherit;font-size:14px;border:1px solid var(--line);background:transparent;color:var(--fg);border-radius:6px;padding:4px 12px;cursor:default}
.note{font-size:13.5px;color:var(--mut);margin:2px 0 0}
.meter{display:inline-flex;align-items:center;gap:8px}
.meter i{display:inline-block;width:80px;height:6px;border-radius:3px;background:var(--line);overflow:hidden}
.meter s{display:block;height:100%;background:var(--grn)}
.empty{color:var(--mut);margin:0}
details{border-top:1px solid var(--line)}
details:last-of-type{border-bottom:1px solid var(--line)}
summary{cursor:pointer;padding:14px 4px;display:flex;gap:10px;align-items:baseline;list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"\25B8";color:var(--mut);width:1em}
details[open] summary::before{content:"\25BE"}
summary .n{font-weight:600}
summary .c{margin-left:auto;color:var(--mut);font-size:14px}
.k-run .n{color:var(--yel)}
.k-know .n{color:var(--blue)}
.k-dec .n{color:var(--pur)}
.k-pr .n{color:var(--fg)}
.k-done .n{color:var(--grn)}
.k-end .n{color:var(--mut)}
.k-chk .n{color:var(--mut)}
details ul{margin:0 0 16px 28px;padding:0;list-style:none;display:flex;flex-direction:column;gap:8px;font-size:15px}
details li .mut{font-size:14px}
.red{color:var(--red)}
`

// The compact toggle sits on <body> itself, so its rule is written whole.
const CSS = `*{box-sizing:border-box}${scope('term', TERM_CSS)}${scope('web', WEB_CSS)}body[data-look=term].compact .sub{display:none}`

// The page's own script: reads the JSON block and draws the route in location.hash with textContent only. No innerHTML.
const SCRIPT = String.raw`
(function(){
var D=JSON.parse(document.getElementById('data').textContent),NOW=D.builtAt,W=D.words,STALE=__STALE__,app=document.getElementById('app');
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
function line(cls,parts){var d=node('div','l'+(cls?' '+cls:''));parts.forEach(function(p){if(p==null||p===false)return;if(typeof p==='string'){d.appendChild(document.createTextNode(p));return}var h=p[2],a=h?node('a',p[0],p[1]):node('span',p[0],p[1]);if(p[3]){a.style.display='inline-block';a.style.minWidth=p[3]+'ch'}if(h){if(h.charAt(0)==='#'){a.href=h}else if(h.indexOf('https://')===0){a.href=h;a.target='_blank';a.rel='noopener noreferrer'}}d.appendChild(a)});return d}
function L(){return line('',[].slice.call(arguments))}
function SUB(){return line('sub',[].slice.call(arguments))}
function head(label,cls,extra){return L([cls||'b',label],extra?'  ':null,extra?['d',extra]:null)}
function rule(){return node('div','rule')}
function bar(done,total,n){n=n||6;var f=total>0?Math.round(done/total*n):0;return [['g',new Array(f+1).join('▓')],['d',new Array(n-f+1).join('░')]]}
function glyph(s){return s.state==='needs-you'?['r','●']:s.state==='running'?['y','◐']:s.state==='done'?['g','✓']:['d','○']}
function isComplete(x){return /^(done|merged)\b/.test(x)}
function fglyph(x){return isComplete(x)?['g','✓']:/^building\b/.test(x)?['y','◐']:/^blocked\b/.test(x)?['r','✗']:['d','○']}
function verdictCls(v){return v==null?'d':/^met/.test(v)?'g':/^partial/.test(v)?'y':/^(missing|contradicts)/.test(v)?'r':'d'}
function sesName(s){return s.repo+'/'+(s.branch||s.title)}
function sessions(f){return D.sessions.filter(f)}
function repoOf(l){return D.repos.filter(function(r){return r.label===l})[0]||null}
function sesById(i){return D.sessions.filter(function(s){return s.id===i})[0]||null}
function msOf(l,slug){var r=repoOf(l);return r?D.milestones.filter(function(m){return m.repoPath===r.path&&m.slug===slug})[0]||null:null}
function prOf(r,branch){return r&&r.prs&&r.prs.ghOk?r.prs.list.filter(function(p){return p.branch===branch})[0]||null:null}
function crumbs(list){var parts=[];list.forEach(function(c,i){if(i>0)parts.push(' › ');parts.push(c[1]?['d',c[0],c[1]]:['b',c[0]])});return line('',parts)}

function top(el,trail,right){
  var b=node('div','bar');var left=node('div');left.appendChild(trail);b.appendChild(left);
  var r=node('div');r.appendChild(right||document.createTextNode(''));b.appendChild(r);el.appendChild(b)}
function age(){var ms=Date.now()-NOW;return ms>STALE?line('',[['y','No session is updating this page. Last build '+dur(ms)+' ago.']]):null}
function toolbar(right){
  var w=node('span','r2');if(right)w.appendChild(right);var c=node('button',null,document.body.classList.contains('compact')?'Details':'Compact');
  c.type='button';c.addEventListener('click',function(){var on=!document.body.classList.contains('compact');document.body.classList.toggle('compact',on);try{localStorage.setItem('agent-tracker-compact',on?'1':'0')}catch(e){}c.textContent=on?'Details':'Compact'});
  w.appendChild(c);return w}
function page(trail,body,right){document.body.setAttribute('data-look','term');app.textContent='';top(app,trail,toolbar(right));var a=age();if(a)app.appendChild(a);app.appendChild(rule());body.forEach(function(n){app.appendChild(n)})}

function notesBlock(kind,title,cls,mark,list,out,withRepo){
  var mine=list.filter(function(x){return x.n.kind===kind});if(!mine.length)return;
  var unseen=mine.filter(function(x){return !x.n.seen}),seen=mine.filter(function(x){return x.n.seen});
  unseen.sort(function(a,b){return b.n.at-a.n.at});seen.sort(function(a,b){return b.n.at-a.n.at});
  out.push(L([cls,title],'  ',unseen.length?[cls,unseen.length+' new']:['d','none new']));
  unseen.forEach(function(x){out.push(L([cls,mark],' ',[null,withRepo?x.s.repo+'/'+x.s.title:x.s.title,H.note(x.s.id,x.n.id)],'  ',['d',clock(x.n.at)]));out.push(SUB('   ',cut(x.n.text,110)))});
  seen.forEach(function(x){out.push(L(['d','· '],['d',x.s.repo+'  '+clock(x.n.at)+'  seen',H.note(x.s.id,x.n.id)]))});
}

// ---- the home page: the owner's web mockup ----
function el(t,c,x){return node(t,c,x)}
function add(p){[].slice.call(arguments,1).forEach(function(c){if(c)p.appendChild(c)});return p}
function sec(ms){var s=Math.floor(Math.max(0,ms)/1000);return s<60?s+'s':dur(ms)}
function hm(ms){var d=new Date(ms);return two(d.getHours())+':'+two(d.getMinutes())}
function asked(ms){var m=midnight();return ms>=m?'today '+hm(ms):ms>=m-864e5?'yesterday '+hm(ms):['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][new Date(ms).getDay()]+' '+hm(ms)}
function link(text,href){var a=el('a',null,text);a.href=href;return a}
function mark(t){var c=t.status==='needs-you'?'● You: ':t.status==='forgotten'?'⚠ Forgotten: ':t.status==='superseded'?'? Superseded? ':'◐ In progress';
  if(t.status==='superseded')return c+(t.later?'A later ask at '+(t.later.at>=midnight()?hm(t.later.at):asked(t.later.at))+', “'+t.later.text+'”, may have replaced it':'A later ask may have replaced it');
  return c+(t.status==='in-progress'?'':t.detail)}
function taskRow(t){
  var li=el('li','row'+({'needs-you':' need',forgotten:' lost',superseded:' sup'}[t.status]||''));
  add(li,el('p','ask',t.text));
  var line=el('div','line');add(line,el('b',null,t.repo),el('span',null,'asked '+asked(t.at)));li.appendChild(line);
  var foot=el('div','foot');foot.appendChild(el('span','status',mark(t)));
  if(t.status==='in-progress'&&t.progress){var pc=t.progress.total?Math.round(t.progress.done/t.progress.total*100):0,m=el('span','meter'),i=el('i'),s=el('s');s.style.width=pc+'%';i.appendChild(s);add(m,i,document.createTextNode(t.progress.slug+', '+t.progress.done+' of '+t.progress.total+' features'));foot.appendChild(m)}
  var open=link('Open session',H.ses(t.sessionId));
  if(t.status!=='superseded'){add(foot,el('span','grow'),open);li.appendChild(foot);return li}
  li.appendChild(foot);
  var f2=el('div','foot');
  ['Keep','Close'].forEach(function(w){var b=el('button',null,w);b.type='button';b.setAttribute('aria-disabled','true');f2.appendChild(b)});
  add(f2,el('span','grow'),open);li.appendChild(f2);
  li.appendChild(el('p','note','Keep and Close are chosen in the terminal pane.'));
  return li}
var CAP=5;
function group(cls,name,count,items,more){
  var d=el('details',cls),s=el('summary');add(s,el('span','n',name),el('span','c',count));d.appendChild(s);
  var u=el('ul');if(!items.length)u.appendChild(el('li','mut','Nothing.'));items.slice(0,CAP).forEach(function(x){u.appendChild(x)});
  if(items.length>CAP)u.appendChild(el('li','mut','and '+(items.length-CAP)+' more'));d.appendChild(u);return d}
function li2(main,mut){var l=el('li');l.appendChild(document.createTextNode(main));if(mut)l.appendChild(el('span','mut',' · '+mut));return l}
function noteLi(x){var l=el('li');if(!x.n.seen)l.appendChild(el('b',null,'New'));l.appendChild(document.createTextNode((x.n.seen?'':' · ')+x.s.repo+' '));l.appendChild(el('span','mut',hm(x.n.at)));l.appendChild(el('br'));l.appendChild(document.createTextNode(x.n.text));return l}
function home(){
  document.body.setAttribute('data-look','web');app.textContent='';
  var live=sessions(function(s){return s.live}),need=D.counts.needsYou,tasks=D.tasks,n=tasks.length;
  var top=el('header','top');
  add(top,el('h1',null,'Agent tracker'),el('p',null,(n?n+' of your tasks '+(n===1?'is':'are')+' not done':D.unchecked.length?'No open task found · '+D.unchecked.length+' not checked':'Every task you gave is done')+' · '+need+(need===1?' needs':' need')+' you now'));
  var fresh=el('span','fresh','Updated '+sec(Date.now()-NOW)+' ago');fresh.setAttribute('role','status');top.appendChild(fresh);app.appendChild(top);
  var old=Date.now()-NOW;
  if(D.loading)app.appendChild(el('p','stale','Reading sessions…'));
  else if(D.stale)app.appendChild(el('p','stale','Session list unavailable. Showing what was last read.'));
  else if(old>STALE)app.appendChild(el('p','stale','No session has updated this page for '+dur(old)+'. What you see is from '+hm(NOW)+'.'));
  var main=el('main');
  var h=el('h2',null,'Your tasks not done yet');main.appendChild(h);
  if(!n)main.appendChild(el('p','empty',D.unchecked.length?'No open task was found. '+D.unchecked.length+' older '+(D.unchecked.length===1?'ask has':'asks have')+' no verdict yet: see Not checked below.':'Nothing is waiting for you.'));
  else{var ol=el('ol','tasks');tasks.forEach(function(t){ol.appendChild(taskRow(t))});main.appendChild(ol)}
  main.appendChild(el('h2',null,'Everything else'));
  var sec2=el('section');sec2.setAttribute('aria-label','Everything else');
  var run=live.filter(function(s){return s.state==='running'}).sort(function(a,b){return (a.since||0)-(b.since||0)});
  sec2.appendChild(group('k-run','Running',String(run.length),run.map(function(s){return li2(s.repo+', '+(s.branch||s.title),s.goalSince?'goal '+dur(NOW-s.goalSince):s.since===null?null:dur(NOW-s.since))})));
  var notes=[];D.sessions.forEach(function(s){s.notes.forEach(function(x){notes.push({s:s,n:x})})});
  notes.sort(function(a,b){return (a.n.seen-b.n.seen)||b.n.at-a.n.at});
  [['know','k-know','You should know'],['decided','k-dec','Decided without you']].forEach(function(k){
    var mine=notes.filter(function(x){return x.n.kind===k[0]}),fresh=mine.filter(function(x){return !x.n.seen}).length;
    sec2.appendChild(group(k[1],k[2],fresh?fresh+' new':'none new',mine.map(noteLi)))});
  var prs=[],fail=0;D.repos.forEach(function(r){if(r.prs&&r.prs.ghOk)r.prs.list.forEach(function(p){if(p.checks==='failing')fail++;prs.push({r:r,p:p})})});
  sec2.appendChild(group('k-pr','Pull requests',prs.length+' open'+(fail?' · '+fail+' failing':''),prs.map(function(x){var l=li2(x.r.label+', '+x.p.title,null),c=el('span',x.p.checks==='failing'?'red':'mut',' · '+W.checks[x.p.checks].replace(/^[✓✗] /,''));l.appendChild(c);return l})));
  var done=live.filter(function(s){return s.state==='done'&&s.lastActivityAt>=midnight()});
  sec2.appendChild(group('k-done','Done today',String(done.length),done.map(function(s){return li2(s.title,s.repo)})));
  var ended=sessions(function(s){return s.state==='ended'&&s.endedAt>=midnight()});
  sec2.appendChild(group('k-end','Ended today',String(ended.length),ended.map(function(s){return li2(s.repo+', '+(s.branch||s.title),hm(s.endedAt))})));
  sec2.appendChild(group('k-chk','Not checked',String(D.unchecked.length),D.unchecked.map(function(u){var l=li2(cut(u.text,90),u.repo+' \u00B7 '+asked(u.at));return l})));
  main.appendChild(sec2);app.appendChild(main);
}

function repoPage(label){
  var r=repoOf(label);if(!r)return missing('No repo named '+label+' has had a session.');
  var ss=sessions(function(s){return s.repoPath===r.path}),out=[],need=ss.filter(function(s){return s.live&&s.state==='needs-you'}).length;
  var ms=D.milestones.filter(function(m){return m.repoPath===r.path});
  if(ms.length){out.push(L(['b','MILESTONES']));ms.forEach(function(m){
    var met=m.facts.filter(function(f){return /^met/.test(f.verdict||'')}).length,fd=m.features.filter(function(f){return isComplete(f.state)}).length;
    var useFacts=m.facts.length>0,pr=prOf(r,m.branch),all=m.features.length>0&&fd===m.features.length;
    out.push(L(all?['g','✓']:['y','◐'],' ',[null,cut(m.slug,24),H.ms(label,m.slug),25],[null,useFacts?met+'/'+m.facts.length+' facts ':fd+'/'+m.features.length+' features ',undefined,16],bar(useFacts?met:fd,useFacts?m.facts.length:m.features.length)[0],bar(useFacts?met:fd,useFacts?m.facts.length:m.features.length)[1],pr?['c','  #'+pr.number,pr.url||undefined]:null,pr?(pr.checks==='pass'?['g',' ✓']:pr.checks==='failing'?['r',' ✗']:['y',' ◌']):null));
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
  page(crumbs([['Home',H.home],[label]]),out,need?L(['r',need+' needs you']):null);
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
  if(ss.length){out.push(rule());out.push(L(['b','SESSIONS']));ss.slice(0,8).forEach(function(s){out.push(L('  ',glyph(s),' ',[null,cut(s.title,60),H.ses(s.id)]))});if(ss.length>8)out.push(L(['d','  and '+(ss.length-8)+' more on the Repo page']))}
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
  if(s.milestone){var m=s.milestone,d=m.features.filter(function(f){return isComplete(f.state)}).length;out.push(rule());out.push(L(['b','MILESTONE'],'  ',['d',m.slug]));if(m.sentence)out.push(L(m.sentence));out.push(L(['d',d+' of '+m.features.length+' features complete '],bar(d,m.features.length)[0],bar(d,m.features.length)[1]));m.features.forEach(function(f){out.push(L('  ',fglyph(f.state),' '+f.n+' '+cut(f.name,70)))})}
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
<script>${SCRIPT.replace('__RELOAD__', String(BOARD_RELOAD_MS)).replace('__STALE__', String(BOARD_STALE_MS))}</script>
</body></html>
`
