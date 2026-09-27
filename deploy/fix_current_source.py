#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "source-current")
app_path = root / "app.js"
index_path = root / "index.html"
style_path = root / "style.css"
sw_path = root / "sw.js"
generator_path = root / "pc-generator" / "HistoScroll_PC_Generator.py"

app = app_path.read_text(encoding="utf-8")
index = index_path.read_text(encoding="utf-8")
style = style_path.read_text(encoding="utf-8")
generator = generator_path.read_text(encoding="utf-8") if generator_path.exists() else ""

# 1) Main feed must use the whole library, not only the 12 editorial clips.
app = app.replace("kind:'editorial',topic:'',status:'unseen'", "kind:'all',topic:'',status:'unseen'")
index = index.replace(
    '<button class="selected" data-kind="editorial">Erklärt</button><button data-kind="focus">Fokus</button><button data-kind="all">Alles</button><button data-kind="excerpt">Originalpassagen</button>',
    '<button data-kind="editorial">Erklärt</button><button data-kind="focus">Fokus</button><button class="selected" data-kind="all">Alles</button><button data-kind="excerpt">Originalpassagen</button>'
)

# 2) Keep one action only in the visible UI and put it into the top bar so it can never cover card text.
old_top = '''<div class="player-top"><div class="player-badges"><span class="pill" id="clipCategory">Histologie</span><span class="seen-badge" id="seenBadge" hidden>✓ Gesehen</span></div><button class="icon-button" id="soundBtn" aria-label="Vorlesen aktivieren" aria-pressed="false">♪<span id="soundLabel">Ton aus</span></button></div><div class="clip-actions" aria-label="Clip-Aktionen"><button id="likeBtn" class="clip-action" aria-label="Gefällt mir" aria-pressed="false"><span>♡</span><small>Like</small></button><button id="favoriteBtn" class="clip-action" aria-label="Favorit" aria-pressed="false"><span>☆</span><small>Merken</small></button></div>'''
new_top = '''<div class="player-top"><div class="player-badges"><span class="pill" id="clipCategory">Histologie</span><span class="seen-badge" id="seenBadge" hidden>✓ Gesehen</span></div><div class="player-top-actions"><button class="icon-button" id="soundBtn" aria-label="Vorlesen aktivieren" aria-pressed="false">♪<span id="soundLabel">Ton aus</span></button><button id="likeBtn" class="top-like-button" aria-label="Gefällt mir" aria-pressed="false"><span>♡</span><small>Like</small></button><button id="favoriteBtn" hidden aria-label="Favorit" aria-pressed="false"><span>☆</span><small>Merken</small></button></div></div>'''
if old_top in index:
    index = index.replace(old_top, new_top)
elif 'class="player-top-actions"' not in index:
    raise SystemExit("Expected player action markup not found")

# 3) Replace the mixed touch/click implementation with one Pointer Events state machine.
start = "let wheel=0,wheelAt=0,touchY=0,lastSwipeAt=0,holdTimer=null,holdPointerId=null;"
end = "$('#sceneText').addEventListener"
if start in app:
    a = app.index(start)
    b = app.index(end, a)
    gesture = r'''let wheel=0,wheelAt=0,holdTimer=null,gesture=null;
const player=$('#player');
const navSafeTarget=t=>t.closest('button,a,input,select,textarea,video,.clip-actions,.progress,.real-video-wrap,.player-bottom,.play-controls,.clip-meta,[data-no-nav],.quiz-option,.reveal-toggle');
const scrollableScene=t=>{const box=t.closest('#sceneContent');return box&&box.scrollHeight>box.clientHeight+2?box:null;};
function cancelHoldTimer(){if(holdTimer){clearTimeout(holdTimer);holdTimer=null;}}
function resumeFromHold(){if(!state.holdPaused)return;state.holdPaused=false;player.classList.remove('hold-paused');if(state.holdWasPlaying)setPlaying(true);}
function clearGesture({resume=true}={}){cancelHoldTimer();gesture=null;if(resume)resumeFromHold();}
player.addEventListener('pointerdown',e=>{
 if(e.isPrimary===false)return;
 if(e.pointerType==='mouse'&&e.button!==0)return;
 if(navSafeTarget(e.target))return;
 const scrollBox=scrollableScene(e.target);
 gesture={id:e.pointerId,startX:e.clientX,startY:e.clientY,lastX:e.clientX,lastY:e.clientY,startedAt:performance.now(),moved:false,longPressed:false,scrollBox};
 state.holdWasPlaying=state.playing;
 try{player.setPointerCapture(e.pointerId);}catch{}
 cancelHoldTimer();
 holdTimer=setTimeout(()=>{
   if(!gesture||gesture.id!==e.pointerId||gesture.moved)return;
   holdTimer=null;gesture.longPressed=true;state.holdPaused=true;state.ignoreClickUntil=Date.now()+500;setPlaying(false);player.classList.add('hold-paused');
 },220);
});
player.addEventListener('pointermove',e=>{
 if(!gesture||e.pointerId!==gesture.id)return;
 const stepY=e.clientY-gesture.lastY;
 const dx=e.clientX-gesture.startX,dy=e.clientY-gesture.startY;
 gesture.lastX=e.clientX;gesture.lastY=e.clientY;
 if(Math.hypot(dx,dy)>12){gesture.moved=true;cancelHoldTimer();}
 if(gesture.scrollBox&&gesture.moved){gesture.scrollBox.scrollTop-=stepY;e.preventDefault();}
});
function finishPointer(e,cancelled=false){
 if(!gesture||e.pointerId!==gesture.id)return;
 const g=gesture;cancelHoldTimer();
 try{if(player.hasPointerCapture?.(e.pointerId))player.releasePointerCapture(e.pointerId);}catch{}
 gesture=null;
 if(g.longPressed||state.holdPaused){resumeFromHold();state.ignoreClickUntil=Date.now()+500;return;}
 if(cancelled)return;
 const dx=e.clientX-g.startX,dy=e.clientY-g.startY,travel=Math.hypot(dx,dy),elapsed=performance.now()-g.startedAt;
 if(g.scrollBox&&travel>12)return;
 if(Math.abs(dy)>55&&Math.abs(dy)>Math.abs(dx)*1.15){dy>0?nextClip():prevClip();return;}
 if(travel<=18&&elapsed<600){const rect=player.getBoundingClientRect(),x=e.clientX-rect.left;x<rect.width/2?sceneStep(-1):sceneStep(1);}
}
player.addEventListener('pointerup',e=>finishPointer(e,false));
player.addEventListener('pointercancel',e=>finishPointer(e,true));
window.addEventListener('blur',()=>clearGesture());
player.addEventListener('wheel',e=>{const box=$('#sceneContent');if(box.scrollHeight>box.clientHeight+2&&e.target.closest('#sceneContent'))return;e.preventDefault();if(Date.now()-wheelAt<650)return;wheel+=e.deltaY;if(Math.abs(wheel)>65){wheel>0?nextClip():prevClip();wheel=0;wheelAt=Date.now();}},{passive:false});
'''
    app = app[:a] + gesture + app[b:]
elif "const player=$('#player');" not in app:
    raise SystemExit("Expected legacy gesture block not found")

# 4) UI overrides: no floating action rail, reclaim text width, clear active Like state.
marker = "/* V6: consolidated feed/gesture fixes */"
if marker not in style:
    style += r'''

/* V6: consolidated feed/gesture fixes */
.player-top-actions{display:flex;align-items:center;gap:10px;flex-shrink:0}
.top-like-button{display:flex;align-items:center;gap:4px;padding:5px 8px;border:1px solid #ffffff2b;border-radius:999px;background:#10151355;color:#f4f4e8;min-height:34px}
.top-like-button span{font-size:1.15rem;line-height:1}.top-like-button small{font-size:.62rem;color:inherit}
.top-like-button.active{background:var(--lime);border-color:var(--lime);color:var(--ink)}
#favoriteBtn[hidden]{display:none!important}
@media(max-width:740px){
 body.feed-active .player-top{padding-right:14px}
 body.feed-active .scene-content{padding:17px 18px 8px}
 body.feed-active .player-top-actions{gap:7px}
 body.feed-active .top-like-button{padding:4px 7px;min-height:32px}
 body.feed-active .top-like-button small{display:none}
}
'''

# 5) Exported MP4s: reserve the lower third for native browser/mobile video controls.
#    Also make the high-quality Edge neural voice the practical default rather than a fast robotic read.
if generator:
    generator = generator.replace(
        "panel=cover_crop(src,(940,430)).filter(ImageFilter.GaussianBlur(.15)); im.paste(panel,(70,y)); y+=475; draw=ImageDraw.Draw(im)",
        "panel=cover_crop(src,(940,320)).filter(ImageFilter.GaussianBlur(.15)); im.paste(panel,(70,y)); y+=365; draw=ImageDraw.Draw(im)"
    )
    generator = generator.replace(
        "if y+len(lines)*(body_size+18)<1600: break",
        "if y+len(lines)*(body_size+18)<1260: break"
    )
    old_footer = """    # footer\n    pages=clip.get('pages') or []; page='Buchseite '+', '.join(map(str,pages)) if pages else 'Eigene Passage'\n    draw.rounded_rectangle((60,1740,1020,1850),24,fill=(8,18,14))\n    draw.text((85,1765),book_title[:54],font=font(25,True),fill=TEXT)\n    draw.text((85,1805),page,font=font(23),fill=MUTED)\n"""
    new_footer = """    # Native player controls can cover roughly the lower third on mobile/desktop.\n    # Keep required text above y=1260 and place source metadata unobtrusively in the header.\n    pages=clip.get('pages') or []; page='Buchseite '+', '.join(map(str,pages)) if pages else 'Eigene Passage'\n    draw.text((1010,72),page,font=font(23,True),fill=MUTED,anchor='ra')\n    draw.text((1010,112),book_title[:38],font=font(20),fill=MUTED,anchor='ra')\n"""
    if old_footer in generator:
        generator = generator.replace(old_footer, new_footer)
    generator = generator.replace(
        "def generate_package(package_path:Path,out_dir:Path,count:int=0,voice='de-DE-KatjaNeural',rate='+0%',kinds:set[str]|None=None,progress:Callable[[str],None]=print):",
        "def generate_package(package_path:Path,out_dir:Path,count:int=0,voice='de-DE-KatjaNeural',rate='-5%',kinds:set[str]|None=None,progress:Callable[[str],None]=print):"
    )
    generator = generator.replace(
        "self.rate=tk.StringVar(value='+0%')",
        "self.rate=tk.StringVar(value='-5%')"
    )
    generator = generator.replace(
        "values=['-10%','+0%','+10%','+20%']",
        "values=['-15%','-10%','-5%','+0%','+10%']"
    )

app_path.write_text(app, encoding="utf-8")
index_path.write_text(index, encoding="utf-8")
style_path.write_text(style, encoding="utf-8")
if generator:
    generator_path.write_text(generator, encoding="utf-8")

if sw_path.exists():
    sw = sw_path.read_text(encoding="utf-8")
    sw = sw.replace("histoscroll-pages-v8", "histoscroll-pages-v9")
    sw_path.write_text(sw, encoding="utf-8")

print("Applied consolidated HistoScroll V7 fixes")
