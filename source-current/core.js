export function cleanText(t){return t.normalize('NFKC').replace(/(\p{L})-\s*\n\s*(\p{L})/gu,'$1$2').replace(/\s+/g,' ').trim();}
export function splitSentences(t){return [...new Intl.Segmenter('de',{granularity:'sentence'}).segment(t)].map(s=>s.segment.trim()).filter(Boolean);}
export function chunks(t,max=260){const sentences=splitSentences(t);let out=[],current='';for(const s of sentences){if(current.length+s.length>max&&current){out.push(current);current='';}if(s.length>max*2){for(const word of s.split(/\s+/)){if(current.length+word.length>max&&current){out.push(current);current='';}current+=(current?' ':'')+word;}}else current+=(current?' ':'')+s;}if(current)out.push(current);return out;}
export function generateClips(pages,bookId,category){const result=[],seen=new Set();for(const p of pages){const cleaned=cleanText(p.text);if(cleaned.length<100)continue;let group='';const add=()=>{if(group.length<100||seen.has(group)){group='';return;}seen.add(group);const scenes=chunks(group);result.push({id:bookId+'-'+result.length,bookId,kind:'excerpt',category,title:group.split(/\s+/).slice(0,8).join(' ').replace(/[.,;:]$/,'')+' …',pages:p.bookPage?[p.bookPage]:[],pdfPages:p.pdfPage?[p.pdfPage]:[],scenes:scenes.map((text,i)=>({label:'Originalpassage · '+(i+1)+'/'+scenes.length,text})),source:group});group='';};for(const sentence of splitSentences(cleaned)){if(group.split(/\s+/).length>90)add();group+=(group?' ':'')+sentence;}add();}return result;}
export function makeFocusClip(sourceClip,bookId,index=0){
 const source=cleanText(sourceClip.source||'');
 if(source.length<60)throw Error('Quelltext für Fokusclip zu kurz.');
 const sourceChunks=chunks(source,190).slice(0,3);
 const sentences=splitSentences(source);
 const answer=sentences.find(s=>s.length>=55&&s.length<=230)||sentences.find(s=>s.length>=30)||sourceChunks[0];
 const title=(sourceClip.title||sentences[0]||'Fokus aus dem Lehrbuch').replace(/\s+/g,' ').trim().slice(0,120);
 const scenes=sourceChunks.map((text,i)=>({label:i===0?'Fokus aus dem Lehrbuch':'Direkt aus der Quelle',text}));
 scenes.push({label:'Denk kurz nach',text:'Was ist der zentrale Zusammenhang in diesem Abschnitt? Formuliere ihn kurz selbst.'});
 scenes.push({label:'Auflösung',text:answer});
 return {id:bookId+'-'+index,bookId,kind:'focus',category:sourceClip.category||'Lehrbuch',title,pages:Array.isArray(sourceClip.pages)?[...sourceClip.pages]:[],pdfPages:Array.isArray(sourceClip.pdfPages)?[...sourceClip.pdfPages]:[],source,scenes,originBookId:sourceClip.bookId||'',sourceClipId:sourceClip.id||''};
}
export function shuffle(items){let a=[...items];for(let i=a.length-1;i>0;i--){let j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
export function duration(scene){return Math.max(scene.label==='Denk kurz nach'?7:5,String(scene.text||scene.interactive?.prompt||scene.interactive?.question||'').split(/\s+/).length/2.5+1.5);}

function parseFrontmatter(text){
 const src=String(text||'').replace(/\r\n?/g,'\n');
 if(!src.startsWith('---\n')) return [{},src];
 const end=src.indexOf('\n---\n',4);
 if(end===-1) return [{},src];
 const block=src.slice(4,end), body=src.slice(end+5);
 const out={};
 for(const line of block.split('\n')){
  const m=line.match(/^([A-Za-z0-9_\-]+):\s*(.*)$/);
  if(m) out[m[1].toLowerCase()]=m[2].trim();
 }
 return [out,body];
}
function parseInteractiveBlock(raw,label='Interaktiv'){
 const text=String(raw||'').trim();
 const reveal=text.match(/^:::reveal\n([\s\S]*?)\n:::\s*$/i);
 if(reveal){
  const block=reveal[1].trim();
  let prompt='',answer='';
  const pm=block.match(/(?:^|\n)prompt:\s*([\s\S]*?)(?=\nanswer:|$)/i);
  const am=block.match(/(?:^|\n)answer:\s*([\s\S]*?)$/i);
  if(pm) prompt=pm[1].trim();
  if(am) answer=am[1].trim();
  if(!prompt && block.includes('\n---\n')){
   const parts=block.split(/\n---\n/);
   prompt=(parts.shift()||'').trim();
   answer=parts.join('\n---\n').trim();
  }
  return {label,text:prompt||answer,interactive:{type:'reveal',prompt:prompt||'Denke kurz nach.',answer:answer||''}};
 }
 const mcq=text.match(/^:::mcq\n([\s\S]*?)\n:::\s*$/i);
 if(mcq){
  const lines=mcq[1].trim().split('\n');
  let question='', explanation='';
  const options=[];
  for(const line of lines){
   const t=line.trim(); if(!t) continue;
   if(/^question:/i.test(t)){question=t.replace(/^question:/i,'').trim();continue;}
   if(/^explanation:/i.test(t)){explanation=t.replace(/^explanation:/i,'').trim();continue;}
   if(/^[+*-]\s+/.test(t)) options.push({text:t.replace(/^[+*-]\s+/,'').trim(),correct:/^\+\s+/.test(t)});
  }
  if(options.length) return {label,text:question||'Wähle die richtige Antwort.',interactive:{type:'mcq',question:question||'Wähle die richtige Antwort.',options,explanation}};
 }
 return {label,text};
}
function parseScenes(text){
 const body=String(text||'').trim();
 const sceneRe=/^#{1,3}\s*(?:SCENE|SZENE|SLIDE)\s*\d*\s*(?:\|\s*(.+))?$/gim;
 const matches=[...body.matchAll(sceneRe)];
 if(!matches.length) return [parseInteractiveBlock(body,'Originalpassage')];
 const scenes=[];
 for(let i=0;i<matches.length;i++){
  const start=matches[i].index+matches[i][0].length;
  const end=i+1<matches.length?matches[i+1].index:body.length;
  const label=(matches[i][1]||`Szene ${i+1}`).trim();
  scenes.push(parseInteractiveBlock(body.slice(start,end).trim(),label));
 }
 return scenes.filter(s=>s.text||s.interactive);
}
export function markdownToPackage(text,fallbackName='Markdown-Import'){
 const [bookFm, bodyRaw]=parseFrontmatter(text);
 const body=String(bodyRaw||'').trim();
 if(!body) throw Error('Leere Markdown-Datei.');
 const clipRe=/^##\s+CLIP\b.*$/gim;
 const clipMatches=[...body.matchAll(clipRe)];
 const clipSections=[];
 if(clipMatches.length){
  for(let i=0;i<clipMatches.length;i++){
   const start=clipMatches[i].index+clipMatches[i][0].length;
   const end=i+1<clipMatches.length?clipMatches[i+1].index:body.length;
   clipSections.push(body.slice(start,end).trim());
  }
 } else clipSections.push(body);
 const bookId='book-'+crypto.randomUUID();
 const clips=clipSections.map((section,idx)=>{
  let title=`${bookFm.book_title||bookFm.title||fallbackName.replace(/\.[^.]+$/,'')} · Clip ${idx+1}`;
  let category='Lehrbuch', kind='excerpt', source='', originBookId='', sourceClipId='';
  let pages=[], pdfPages=[];
  const sceneHeaderIdx=section.search(/^#{1,3}\s*(?:SCENE|SZENE|SLIDE)\b/im);
  const metaBlock=(sceneHeaderIdx>=0?section.slice(0,sceneHeaderIdx):'').trim();
  for(const raw of metaBlock.split('\n')){
   const m=raw.match(/^([A-Za-z0-9_\-]+):\s*(.*)$/); if(!m) continue;
   const k=m[1].toLowerCase(), v=m[2].trim();
   if(k==='title') title=v||title;
   else if(['topic','category'].includes(k)) category=v||category;
   else if(k==='kind') kind=v||kind;
   else if(k==='pages') pages=v? v.split(',').map(x=>Number(x.trim())).filter(Boolean):[];
   else if(['pdf_pages','pdfpages'].includes(k)) pdfPages=v? v.split(',').map(x=>Number(x.trim())).filter(Boolean):[];
   else if(k==='source') source=v;
   else if(['origin_book_id','originbookid'].includes(k)) originBookId=v||'';
   else if(['source_clip_id','sourceclipid'].includes(k)) sourceClipId=v||'';
  }
  const sceneBody=sceneHeaderIdx>=0?section.slice(sceneHeaderIdx):section;
  const scenes=parseScenes(sceneBody);
  if(!source) source=scenes.map(s=>s.interactive?.prompt||s.interactive?.question||s.text||'').filter(Boolean).join(' ');
  return {id:`${bookId}-${idx}`,bookId,kind:['editorial','focus','excerpt'].includes(kind)?kind:'excerpt',category,title,pages,pdfPages,source,scenes,originBookId,sourceClipId};
 }).filter(c=>c.scenes.length);
 return {id:bookId,title:bookFm.book_title||bookFm.title||fallbackName.replace(/\.[^.]+$/,''),author:bookFm.author||'Eigener Import',edition:bookFm.edition||'Markdown-Import',pageCount:Number(bookFm.page_count||bookFm.pagecount)||0,generatedFrom:bookFm.generated_from||bookFm.generatedfrom||null,clips};
}
export function packageToMarkdown(book){
 const esc=s=>String(s??'').replace(/\r\n?/g,'\n').trim();
 const header=['---',`book_title: ${esc(book.title||'Unbenannt')}`,`author: ${esc(book.author||'Eigener Import')}`,`edition: ${esc(book.edition||'HistoScroll-Export')}`,`page_count: ${Number(book.pageCount)||0}`,book.generatedFrom?`generated_from: ${esc(book.generatedFrom)}`:null,'---',''].filter(v=>v!==null).join('\n');
 const clips=(book.clips||[]).map((c,idx)=>{
  const meta=['## CLIP',`title: ${esc(c.title||`Clip ${idx+1}`)}`,`category: ${esc(c.category||'Lehrbuch')}`,`kind: ${esc(c.kind||'excerpt')}`,c.pages?.length?`pages: ${c.pages.join(', ')}`:null,c.pdfPages?.length?`pdf_pages: ${c.pdfPages.join(', ')}`:null,c.originBookId?`origin_book_id: ${esc(c.originBookId)}`:null,c.sourceClipId?`source_clip_id: ${esc(c.sourceClipId)}`:null,''].filter(v=>v!==null).join('\n');
  const scenes=(c.scenes||[]).map((s,i)=>{
   const label=esc(s.label||`Szene ${i+1}`);
   if(s.interactive?.type==='reveal') return `### SCENE ${i+1} | ${label}\n:::reveal\nprompt: ${esc(s.interactive.prompt||s.text||'')}\nanswer: ${esc(s.interactive.answer||'')}\n:::\n`;
   if(s.interactive?.type==='mcq') return `### SCENE ${i+1} | ${label}\n:::mcq\nquestion: ${esc(s.interactive.question||s.text||'')}\n${(s.interactive.options||[]).map(o=>`${o.correct?'+':'-'} ${esc(o.text||'')}`).join('\n')}\n${s.interactive.explanation?`explanation: ${esc(s.interactive.explanation)}`:''}\n:::\n`;
   return `### SCENE ${i+1} | ${label}\n${esc(s.text||'')}\n`;
  }).join('\n');
  return `${meta}${scenes}`.trim();
 }).join('\n\n');
 return `${header}${clips}\n`;
}
export function validatePackage(b){return b&&typeof b.title==='string'&&b.title.length<=200&&Array.isArray(b.clips)&&b.clips.length>0&&b.clips.length<=15000&&b.clips.every(c=>typeof c.source==='string'&&typeof c.title==='string'&&Array.isArray(c.scenes)&&c.scenes.length>0&&c.scenes.every(s=>typeof s.label==='string'&&(((typeof s.text==='string')&&s.text.length<=2500)||(['reveal','mcq'].includes(s.interactive?.type)))));}
