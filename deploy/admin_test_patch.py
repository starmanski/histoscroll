from pathlib import Path
import sys

root = Path(sys.argv[1])
app_path = root / 'app.js'
cloud_path = root / 'cloud.js'
index_path = root / 'index.html'
style_path = root / 'style.css'
sw_path = root / 'sw.js'

app = app_path.read_text(encoding='utf-8')
app = app.replace(
    "import {configured,restoreSession,requestOtp,verifyOtp,signOut,currentUser,books as cloudBooks,media} from './cloud.js';",
    "import {configured,restoreSession,requestOtp,verifyOtp,signOut,currentUser,isAdmin as cloudIsAdmin,books as cloudBooks,media} from './cloud.js';"
)
app = app.replace(
    "let pdfDoc=null,pending=null,importMode='pdf',importBusy=false,exportCancelled=false,exporting=false,lastFrame=performance.now(),speechToken=0,voiceWaitTimer=null,exportUrl=null,deferredInstallPrompt=null,realVideoToken=0;",
    "let pdfDoc=null,pending=null,importMode='pdf',importBusy=false,exportCancelled=false,exporting=false,lastFrame=performance.now(),speechToken=0,voiceWaitTimer=null,exportUrl=null,deferredInstallPrompt=null,realVideoToken=0;\nlet adminDemo=false,cloudAdmin=false;\nconst ADMIN_DEMO_FLAG='histoscroll-admin-demo-v1';\nconst DEMO_DB='histoscroll-admin-demo-db-v1';"
)
old_api = """async function api(path,options={}){\n const list=path==='/api/books',m=path.match(/^\\/api\\/books\\/([a-zA-Z0-9-]{1,100})$/);\n if(list&&(!options.method||options.method==='GET'))return cloudBooks.list();\n if(!m)throw Error('Ungültiger Speicherpfad.');\n const id=m[1],method=options.method||'GET';\n if(method==='GET')return cloudBooks.get(id);\n if(method==='DELETE')return cloudBooks.remove(id);\n if(method==='PUT'){const b=typeof options.body==='string'?JSON.parse(options.body):options.body;return cloudBooks.put(b);}\n throw Error('Nicht unterstützte Speichermethode.');\n}"""
new_api = """function demoDb(){return new Promise((resolve,reject)=>{const req=indexedDB.open(DEMO_DB,1);req.onupgradeneeded=()=>{const db=req.result;if(!db.objectStoreNames.contains('books'))db.createObjectStore('books',{keyPath:'id'});};req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error||Error('Lokaler Admin-Speicher konnte nicht geöffnet werden.'));});}\nasync function demoTx(mode,fn){const db=await demoDb();try{return await new Promise((resolve,reject)=>{const tx=db.transaction('books',mode),store=tx.objectStore('books');let result;try{result=fn(store,resolve,reject);}catch(e){reject(e);}tx.onerror=()=>reject(tx.error||Error('Lokaler Admin-Speicherfehler.'));if(result&&typeof result.then==='function')result.catch(reject);});}finally{db.close();}}\nconst demoBooks={\n async list(){return demoTx('readonly',(store,resolve,reject)=>{const r=store.getAll();r.onsuccess=()=>resolve((r.result||[]).map(b=>({id:b.id,title:b.title,author:b.author,edition:b.edition,page_count:b.pageCount||0,clip_count:b.clips?.length||0,generated_from:b.generatedFrom||null,updated_at:b._demoUpdatedAt||''})));r.onerror=()=>reject(r.error);});},\n async get(id){return demoTx('readonly',(store,resolve,reject)=>{const r=store.get(id);r.onsuccess=()=>r.result?resolve(r.result):reject(Error('Buch nicht gefunden.'));r.onerror=()=>reject(r.error);});},\n async put(book){const copy=structuredClone(book);copy._demoUpdatedAt=new Date().toISOString();return demoTx('readwrite',(store,resolve,reject)=>{const r=store.put(copy);r.onsuccess=()=>resolve(copy);r.onerror=()=>reject(r.error);});},\n async remove(id){return demoTx('readwrite',(store,resolve,reject)=>{const r=store.delete(id);r.onsuccess=()=>resolve({ok:true});r.onerror=()=>reject(r.error);});},\n async clear(){return demoTx('readwrite',(store,resolve,reject)=>{const r=store.clear();r.onsuccess=()=>resolve({ok:true});r.onerror=()=>reject(r.error);});}\n};\nasync function api(path,options={}){\n const list=path==='/api/books',m=path.match(/^\\/api\\/books\\/([a-zA-Z0-9-]{1,100})$/);\n const backend=adminDemo?demoBooks:cloudBooks;\n if(list&&(!options.method||options.method==='GET'))return backend.list();\n if(!m)throw Error('Ungültiger Speicherpfad.');\n const id=m[1],method=options.method||'GET';\n if(method==='GET')return backend.get(id);\n if(method==='DELETE')return backend.remove(id);\n if(method==='PUT'){const b=typeof options.body==='string'?JSON.parse(options.body):options.body;return backend.put(b);}\n throw Error('Nicht unterstützte Speichermethode.');\n}"""
if old_api not in app:
    raise SystemExit('admin patch: api block not found')
app = app.replace(old_api, new_api)
app = app.replace(
    '<span class="tiny">Privat im Konto</span>',
    '<span class="tiny">${adminDemo?\'Nur lokal · Admin-Test\':\'Privat im Konto\'}</span>'
)
old_unlock = """function unlockApp(){document.body.classList.remove('auth-locked');$('#authGate').hidden=true;const u=currentUser();const name=u?.user_metadata?.display_name||u?.email?.split('@')[0]||'Konto';$('#accountLabel').textContent=name;$('#accountEmail').textContent=u?.email||'Angemeldet';}\nfunction lockApp(){stopSpeech();document.body.classList.add('auth-locked');$('#authGate').hidden=false;state.books=[];}\nasync function init(){\n if(!configured()){lockApp();$('#configMissing').hidden=false;$('#authForms').hidden=true;return;}\n const restored=await restoreSession();if(!restored){lockApp();return;}unlockApp();await loadRemote();\n}\ninit();"""
new_unlock = """function updateAdminUi(){const active=adminDemo||cloudAdmin;$('#adminBtn').hidden=!active;$('#adminModeBanner').hidden=!adminDemo;$('#adminRole').textContent=adminDemo?'ADMIN-TESTMODUS · nur dieses Gerät':cloudAdmin?'ADMIN':'STANDARDKONTO';$('#adminModeText').textContent=adminDemo?'Du testest HistoScroll ohne E-Mail. Bücher und Clips liegen ausschließlich in diesem Browser/PWA und werden nicht zu Supabase synchronisiert.':cloudAdmin?'Dieses Konto ist als HistoScroll-Administrator markiert. Cloud-Synchronisierung ist aktiv.':'Dieses Konto hat keine Admin-Rechte.';$('#leaveAdminDemo').hidden=!adminDemo;$('#clearAdminDemo').hidden=!adminDemo;$('#syncBtn').title=adminDemo?'Lokale Testbibliothek neu laden':'Bibliothek synchronisieren';}\nfunction unlockApp(){document.body.classList.remove('auth-locked');$('#authGate').hidden=true;const u=currentUser();const name=adminDemo?'Admin-Test':u?.user_metadata?.display_name||u?.email?.split('@')[0]||'Konto';$('#accountLabel').textContent=name;$('#accountEmail').textContent=adminDemo?'Lokaler Admin-Testmodus':u?.email||'Angemeldet';updateAdminUi();}\nfunction lockApp(){stopSpeech();document.body.classList.add('auth-locked');$('#authGate').hidden=false;state.books=[];cloudAdmin=false;updateAdminUi();}\nasync function enterAdminDemo(){adminDemo=true;cloudAdmin=false;try{localStorage.setItem(ADMIN_DEMO_FLAG,'1');}catch{}unlockApp();await loadRemote();toast('Admin-Testmodus aktiv. Daten bleiben nur auf diesem Gerät.');}\nasync function leaveAdminDemo(){adminDemo=false;try{localStorage.removeItem(ADMIN_DEMO_FLAG);}catch{}state.books=[];lockApp();}\nasync function init(){\n try{adminDemo=localStorage.getItem(ADMIN_DEMO_FLAG)==='1';}catch{adminDemo=false;}\n if(adminDemo){unlockApp();await loadRemote();return;}\n if(!configured()){lockApp();$('#configMissing').hidden=false;$('#authForms').hidden=true;return;}\n const restored=await restoreSession();if(!restored){lockApp();return;}cloudAdmin=await cloudIsAdmin().catch(()=>false);unlockApp();await loadRemote();\n}\ninit();"""
if old_unlock not in app:
    raise SystemExit('admin patch: unlock block not found')
app = app.replace(old_unlock, new_unlock)
app = app.replace(
    "$('#verifyOtp').onclick=async()=>{const email=$('#authEmail').value.trim(),token=$('#authOtp').value.trim();if(!email||token.length<4){$('#authStatus').textContent='Bitte E-Mail und Einmalcode eingeben.';return;}const btn=$('#verifyOtp');btn.disabled=true;$('#authStatus').textContent='Code wird geprüft …';try{await verifyOtp(email,token);unlockApp();await loadRemote();$('#authStatus').textContent='';$('#authOtp').value='';}catch(e){$('#authStatus').textContent=e.message;}finally{btn.disabled=false;}};",
    "$('#verifyOtp').onclick=async()=>{const email=$('#authEmail').value.trim(),token=$('#authOtp').value.trim();if(!email||token.length<4){$('#authStatus').textContent='Bitte E-Mail und Einmalcode eingeben.';return;}const btn=$('#verifyOtp');btn.disabled=true;$('#authStatus').textContent='Code wird geprüft …';try{await verifyOtp(email,token);adminDemo=false;cloudAdmin=await cloudIsAdmin().catch(()=>false);unlockApp();await loadRemote();$('#authStatus').textContent='';$('#authOtp').value='';}catch(e){$('#authStatus').textContent=e.message;}finally{btn.disabled=false;}};"
)
app = app.replace(
    "$('#accountBtn').onclick=()=>showDialog('#accountDialog');\n$('#signOutBtn').onclick=async()=>{await signOut();$('#accountDialog').close();lockApp();$('#authOtp').value='';$('#otpStep').hidden=true;$('#authStatus').textContent='';};",
    "$('#adminDemoBtn').onclick=enterAdminDemo;\n$('#accountBtn').onclick=()=>showDialog('#accountDialog');\n$('#adminBtn').onclick=()=>showDialog('#adminDialog');\n$('#leaveAdminDemo').onclick=async()=>{$('#adminDialog').close();await leaveAdminDemo();};\n$('#clearAdminDemo').onclick=async()=>{if(!confirm('Alle lokal im Admin-Testmodus gespeicherten Bücher und Clips löschen?'))return;await demoBooks.clear();state.books=[];rebuild(true);toast('Lokale Admin-Testdaten gelöscht.');};\n$('#signOutBtn').onclick=async()=>{if(adminDemo){$('#accountDialog').close();await leaveAdminDemo();return;}await signOut();$('#accountDialog').close();lockApp();$('#authOtp').value='';$('#otpStep').hidden=true;$('#authStatus').textContent='';};"
)
app = app.replace(
    "$('.brand').onclick=e=>{e.preventDefault();showView('feed');};$('#syncBtn').onclick=async()=>{$('#syncBtn').disabled=true;try{await loadRemote();toast('Bibliothek synchronisiert.');}finally{$('#syncBtn').disabled=false;}};",
    "$('.brand').onclick=e=>{e.preventDefault();showView('feed');};$('#syncBtn').onclick=async()=>{$('#syncBtn').disabled=true;try{await loadRemote();toast(adminDemo?'Lokale Testbibliothek neu geladen.':'Bibliothek synchronisiert.');}finally{$('#syncBtn').disabled=false;}};"
)
app_path.write_text(app, encoding='utf-8')

cloud = cloud_path.read_text(encoding='utf-8')
needle = "async function db(path,options={}){return raw('/rest/v1/'+path,options);}\nasync function storage(path,options={}){return raw('/storage/v1/'+path,options);}\n"
if needle not in cloud:
    raise SystemExit('admin patch: cloud insertion point not found')
cloud = cloud.replace(needle, needle + "export async function isAdmin(){const u=currentUser();if(!u)return false;const rows=await db(`app_admins?user_id=eq.${encodeURIComponent(u.id)}&select=user_id&limit=1`);return !!rows?.length;}\n")
cloud_path.write_text(cloud, encoding='utf-8')

html = index_path.read_text(encoding='utf-8')
html = html.replace(
    '<p id="authStatus" role="status"></p>\n    </div>',
    '<p id="authStatus" role="status"></p>\n      <div class="admin-test-entry"><span class="eyebrow">JETZT TESTEN</span><p>Du kannst HistoScroll sofort ohne E-Mail ausprobieren. Im Admin-Testmodus bleiben alle importierten Bücher und Clips nur auf diesem Gerät.</p><button class="secondary wide" id="adminDemoBtn">Admin-Testmodus starten</button></div>\n    </div>'
)
html = html.replace('<main>\n<header>', '<main>\n<div id="adminModeBanner" class="admin-mode-banner" hidden>ADMIN-TESTMODUS · NUR LOKAL · KEINE CLOUD-SYNCHRONISIERUNG</div>\n<header>')
html = html.replace(
    '<button class="subtle" id="openBooks">▥ <span>Quellen wählen</span></button><button class="subtle account-button" id="accountBtn"',
    '<button class="subtle" id="openBooks">▥ <span>Quellen wählen</span></button><button class="subtle admin-button" id="adminBtn" hidden>⚙ Admin</button><button class="subtle account-button" id="accountBtn"'
)
html = html.replace(
    '<dialog id="accountDialog"><button class="close-dialog" aria-label="Schließen">×</button><span class="eyebrow">KONTO</span><h2 id="accountEmail">Angemeldet</h2><p>Deine Buchpakete sind nur für dieses Konto freigegeben.</p><button id="signOutBtn" class="secondary wide">Abmelden</button></dialog>',
    '<dialog id="accountDialog"><button class="close-dialog" aria-label="Schließen">×</button><span class="eyebrow">KONTO</span><h2 id="accountEmail">Angemeldet</h2><p id="adminRole" class="admin-role">STANDARDKONTO</p><p>Im normalen Kontomodus sind deine Buchpakete nur für dieses Konto freigegeben. Im Admin-Testmodus bleiben sie ausschließlich auf diesem Gerät.</p><button id="signOutBtn" class="secondary wide">Abmelden / Testmodus verlassen</button></dialog>\n<dialog id="adminDialog"><button class="close-dialog" aria-label="Schließen">×</button><span class="eyebrow">ADMIN</span><h2>HistoScroll verwalten</h2><p id="adminModeText"></p><div class="notice"><b>Testmodus:</b> Du kannst PDFs und Clip-Pakete importieren, Fokus-Shorts erzeugen, den Feed testen und Daten lokal behalten. Cloud-Sync und Pi-Video-Uploads benötigen später eine echte Anmeldung.</div><button id="clearAdminDemo" class="secondary wide">Lokale Testdaten löschen</button><button id="leaveAdminDemo" class="text-button wide">Admin-Testmodus verlassen</button></dialog>'
)
index_path.write_text(html, encoding='utf-8')

style = style_path.read_text(encoding='utf-8')
style += "\n.admin-test-entry{margin-top:22px;padding-top:20px;border-top:1px solid var(--line)}.admin-test-entry p{color:var(--muted);font-size:.9rem;line-height:1.45}.admin-mode-banner{margin:0 0 14px;padding:8px 12px;border:1px solid #c6f56755;border-radius:8px;background:#22301f;color:var(--lime);font-size:.75rem;font-weight:800;letter-spacing:.08em;text-align:center}.admin-button{border-color:#c6f56766!important;color:var(--lime)!important}.admin-role{display:inline-block;padding:5px 9px;border-radius:999px;border:1px solid #c6f56755;color:var(--lime);font-size:.75rem;font-weight:800;letter-spacing:.08em}.wide.text-button{width:100%;text-align:center;margin-top:8px}@media(max-width:740px){.admin-mode-banner{font-size:.66rem;margin-bottom:8px}}\n"
style_path.write_text(style, encoding='utf-8')

sw = sw_path.read_text(encoding='utf-8').replace('histoscroll-pages-v3', 'histoscroll-pages-v4')
sw_path.write_text(sw, encoding='utf-8')

print('Admin test patch applied')
