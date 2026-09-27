from __future__ import annotations
import sys, subprocess

def _ensure_deps():
    missing=[]
    try: import PIL
    except Exception: missing.append('Pillow>=11,<12')
    try: import edge_tts
    except Exception: missing.append('edge-tts>=7,<8')
    if missing:
        print('[HistoScroll] Installiere Python-Abhaengigkeiten: '+', '.join(missing))
        subprocess.check_call([sys.executable,'-m','pip','install',*missing])

_ensure_deps()
import argparse, asyncio, base64, io, json, math, os, re, shutil, subprocess, tempfile
from pathlib import Path
from typing import Callable
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import edge_tts

W,H=1080,1920
BG_DEFAULT=(27,55,48); BG_QUESTION=(67,43,38); BG_FOCUS=(55,48,72); BG_EXCERPT=(34,47,64)
TEXT=(244,246,236); MUTED=(196,207,195); LIME=(198,245,103)


def safe_name(s:str)->str:
    s=re.sub(r'[^A-Za-z0-9._-]+','-',s).strip('-._')
    return s[:160] or 'clip'

def run(cmd:list[str], quiet=False):
    p=subprocess.run(cmd, stdout=subprocess.DEVNULL if quiet else None, stderr=subprocess.PIPE, text=True)
    if p.returncode:
        raise RuntimeError((p.stderr or 'FFmpeg-Fehler')[-2500:])

def ffprobe_duration(path:Path)->float:
    p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)],capture_output=True,text=True)
    if p.returncode: raise RuntimeError('ffprobe konnte die Audiodauer nicht lesen: '+p.stderr[-800:])
    return max(0.8,float(p.stdout.strip()))

def find_font(bold=False)->str|None:
    candidates=[]
    if os.name=='nt':
        root=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'
        candidates += [root/('seguisb.ttf' if bold else 'segoeui.ttf'), root/('arialbd.ttf' if bold else 'arial.ttf')]
    candidates += [Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    return next((str(x) for x in candidates if x.exists()),None)

def font(size:int,bold=False):
    fp=find_font(bold)
    return ImageFont.truetype(fp,size) if fp else ImageFont.load_default()

def wrap_text(draw:ImageDraw.ImageDraw,text:str,fnt,max_width:int,max_lines:int|None=None):
    words=re.sub(r'\s+',' ',text.strip()).split(' '); lines=[]; line=''
    for word in words:
        trial=(line+' '+word).strip()
        if draw.textbbox((0,0),trial,font=fnt)[2] <= max_width or not line:
            line=trial
        else:
            lines.append(line); line=word
            if max_lines and len(lines)>=max_lines: break
    if line and (not max_lines or len(lines)<max_lines): lines.append(line)
    if max_lines and len(lines)==max_lines and len(' '.join(lines))<len(' '.join(words)):
        lines[-1]=lines[-1].rstrip(' .')+'…'
    return lines

def decode_image(value:str|None):
    if not value: return None
    try:
        if value.startswith('data:image/'):
            raw=base64.b64decode(value.split(',',1)[1]); return Image.open(io.BytesIO(raw)).convert('RGB')
        p=Path(value)
        if p.exists(): return Image.open(p).convert('RGB')
    except Exception: pass
    return None

def cover_crop(img:Image.Image,size:tuple[int,int]):
    tw,th=size; scale=max(tw/img.width,th/img.height); nw,nh=int(img.width*scale),int(img.height*scale)
    img=img.resize((nw,nh),Image.Resampling.LANCZOS); left=(nw-tw)//2; top=(nh-th)//2
    return img.crop((left,top,left+tw,top+th))

def render_card(clip:dict,scene:dict,out:Path,book_title:str):
    label=str(scene.get('label') or 'Lernclip'); kind=clip.get('kind','editorial')
    bg=BG_QUESTION if label=='Denk kurz nach' else BG_FOCUS if kind=='focus' else BG_EXCERPT if kind=='excerpt' else BG_DEFAULT
    im=Image.new('RGB',(W,H),bg); draw=ImageDraw.Draw(im)
    # soft depth / vignette
    overlay=Image.new('RGBA',(W,H),(0,0,0,0)); od=ImageDraw.Draw(overlay)
    od.ellipse((-250,-500,1350,900),fill=(255,255,255,12)); od.rectangle((0,1500,W,H),fill=(0,0,0,28)); im=Image.alpha_composite(im.convert('RGBA'),overlay).convert('RGB'); draw=ImageDraw.Draw(im)
    draw.text((70,72),'HISTOSCROLL',font=font(28,True),fill=LIME)
    cat=str(clip.get('category') or 'Lernclip')[:48]; draw.text((70,120),cat,font=font(27),fill=MUTED)
    y=190
    src=decode_image(clip.get('image'))
    if src:
        panel=cover_crop(src,(940,430)).filter(ImageFilter.GaussianBlur(.15)); im.paste(panel,(70,y)); y+=475; draw=ImageDraw.Draw(im)
    draw.text((70,y),label.upper()[:55],font=font(25,True),fill=LIME); y+=60
    title=str(clip.get('title') or 'HistoScroll')
    title_font=font(62,True)
    for line in wrap_text(draw,title,title_font,900,4):
        draw.text((70,y),line,font=title_font,fill=TEXT); y+=72
    y+=20
    body=str(scene.get('text') or '')
    body_size=44
    while body_size>=30:
        bf=font(body_size); lines=wrap_text(draw,body,bf,900)
        if y+len(lines)*(body_size+18)<1600: break
        body_size-=2
    for line in lines:
        draw.text((70,y),line,font=bf,fill=TEXT); y+=body_size+18
    # footer
    pages=clip.get('pages') or []; page='Buchseite '+', '.join(map(str,pages)) if pages else 'Eigene Passage'
    draw.rounded_rectangle((60,1740,1020,1850),24,fill=(8,18,14))
    draw.text((85,1765),book_title[:54],font=font(25,True),fill=TEXT)
    draw.text((85,1805),page,font=font(23),fill=MUTED)
    im.save(out,quality=95)

async def tts(text:str,voice:str,rate:str,out:Path):
    comm=edge_tts.Communicate(text=text,voice=voice,rate=rate)
    await comm.save(str(out))

def make_scene_video(png:Path,audio:Path,out:Path,duration:float):
    frames=max(30,int(math.ceil((duration+.35)*30)))
    fade_out=max(.1,duration-.20)
    vf=(f"scale=1120:1992,zoompan=z='min(zoom+0.00045,1.055)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps=30," \
        f"fade=t=in:st=0:d=0.18,fade=t=out:st={fade_out:.3f}:d=0.18,format=yuv420p")
    run(['ffmpeg','-y','-loop','1','-i',str(png),'-i',str(audio),'-vf',vf,'-t',f'{duration+.30:.3f}',
         '-c:v','libx264','-preset','medium','-crf','20','-r','30','-c:a','aac','-b:a','160k','-ar','48000','-ac','2','-shortest',str(out)],quiet=True)

def concat(parts:list[Path],out:Path,tmp:Path):
    lst=tmp/'concat.txt'; lst.write_text('\n'.join("file '"+str(p).replace("'","'\\''")+"'" for p in parts),encoding='utf-8')
    run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(lst),'-c','copy','-movflags','+faststart',str(out)],quiet=True)

def clip_voice_text(clip:dict,scene:dict,index:int):
    title=(str(clip.get('title','')).strip()+'. ') if index==0 else ''
    return title+str(scene.get('text','')).strip()

def generate_one(clip:dict,book_title:str,out_dir:Path,voice:str,rate:str,progress:Callable[[str],None]=print):
    clip_id=safe_name(str(clip.get('id') or 'clip'))
    final=out_dir/(clip_id+'.mp4')
    with tempfile.TemporaryDirectory(prefix='histoscroll-') as td:
        tmp=Path(td); parts=[]
        scenes=clip.get('scenes') or []
        if not scenes: raise RuntimeError('Clip hat keine Szenen: '+clip_id)
        for i,scene in enumerate(scenes):
            progress(f'{clip_id}: Szene {i+1}/{len(scenes)} – Stimme')
            png=tmp/f'{i:02d}.png'; mp3=tmp/f'{i:02d}.mp3'; mp4=tmp/f'{i:02d}.mp4'
            render_card(clip,scene,png,book_title)
            asyncio.run(tts(clip_voice_text(clip,scene,i),voice,rate,mp3))
            dur=ffprobe_duration(mp3)
            progress(f'{clip_id}: Szene {i+1}/{len(scenes)} – Animation')
            make_scene_video(png,mp3,mp4,dur); parts.append(mp4)
        concat(parts,final,tmp)
    return final

def generate_package(package_path:Path,out_dir:Path,count:int=0,voice='de-DE-KatjaNeural',rate='+0%',kinds:set[str]|None=None,progress:Callable[[str],None]=print):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise RuntimeError('FFmpeg/ffprobe fehlt. Installiere FFmpeg unter Windows z. B. mit: winget install --id Gyan.FFmpeg -e . Danach das Generatorfenster neu starten.')
    data=json.loads(package_path.read_text(encoding='utf-8'))
    clips=list(data.get('clips') or [])
    if kinds: clips=[c for c in clips if c.get('kind') in kinds]
    if count>0: clips=clips[:count]
    if not clips: raise RuntimeError('Keine passenden Clips im Paket gefunden.')
    out_dir.mkdir(parents=True,exist_ok=True); manifest=[]
    for i,c in enumerate(clips,1):
        progress(f'Clip {i}/{len(clips)}: {c.get("title","HistoScroll")}')
        path=generate_one(c,data.get('title','HistoScroll'),out_dir,voice,rate,progress)
        manifest.append({'clip_id':c.get('id'),'book_id':c.get('bookId') or data.get('id'),'title':c.get('title'),'file':path.name})
    (out_dir/'histoscroll-video-manifest.json').write_text(json.dumps({'book_id':data.get('id'),'book_title':data.get('title'),'voice':voice,'videos':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
    progress(f'Fertig: {len(manifest)} MP4-Dateien in {out_dir}')
    return manifest

import queue, threading, traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

VOICES=[('Deutsch – Katja (weiblich)','de-DE-KatjaNeural'),('Deutsch – Conrad (männlich)','de-DE-ConradNeural'),('Österreich – Ingrid','de-AT-IngridNeural'),('Schweiz – Leni','de-CH-LeniNeural')]
class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title('HistoScroll PC-Video-Studio'); self.geometry('760x610'); self.minsize(680,540)
        self.pkg=tk.StringVar(); self.out=tk.StringVar(value=str(Path.home()/'Videos'/'HistoScroll'))
        self.count=tk.IntVar(value=10); self.voice=tk.StringVar(value=VOICES[0][1]); self.rate=tk.StringVar(value='+0%'); self.editorial=tk.BooleanVar(value=True); self.focus=tk.BooleanVar(value=True); self.excerpt=tk.BooleanVar(value=False)
        self.q=queue.Queue(); self._build(); self.after(100,self.poll)
    def _build(self):
        f=ttk.Frame(self,padding=20); f.pack(fill='both',expand=True)
        ttk.Label(f,text='HistoScroll PC-Video-Studio',font=('Segoe UI',20,'bold')).pack(anchor='w'); ttk.Label(f,text='Erzeugt echte 9:16-MP4s mit Animation und deutscher Neural-Stimme.').pack(anchor='w',pady=(2,18))
        self.row_file(f,'Clip-Paket (.json)',self.pkg,self.pick_pkg); self.row_file(f,'Ausgabeordner',self.out,self.pick_out)
        g=ttk.Frame(f); g.pack(fill='x',pady=8); ttk.Label(g,text='Anzahl (0 = alle)',width=24).pack(side='left'); ttk.Spinbox(g,from_=0,to=10000,textvariable=self.count,width=10).pack(side='left')
        g=ttk.Frame(f); g.pack(fill='x',pady=8); ttk.Label(g,text='Stimme',width=24).pack(side='left'); cb=ttk.Combobox(g,state='readonly',width=38,values=[x[0] for x in VOICES]); cb.current(0); cb.pack(side='left'); cb.bind('<<ComboboxSelected>>',lambda e:self.voice.set(VOICES[cb.current()][1]))
        g=ttk.Frame(f); g.pack(fill='x',pady=8); ttk.Label(g,text='Sprechtempo',width=24).pack(side='left'); ttk.Combobox(g,textvariable=self.rate,state='readonly',values=['-10%','+0%','+10%','+20%'],width=10).pack(side='left')
        kinds=ttk.LabelFrame(f,text='Clip-Arten',padding=10); kinds.pack(fill='x',pady=10); ttk.Checkbutton(kinds,text='Erklärt',variable=self.editorial).pack(side='left',padx=(0,18)); ttk.Checkbutton(kinds,text='Fokus',variable=self.focus).pack(side='left',padx=(0,18)); ttk.Checkbutton(kinds,text='Originalpassagen',variable=self.excerpt).pack(side='left')
        self.start=ttk.Button(f,text='MP4-Shorts generieren',command=self.go); self.start.pack(fill='x',pady=(8,12),ipady=7)
        self.bar=ttk.Progressbar(f,mode='indeterminate'); self.bar.pack(fill='x'); self.log=tk.Text(f,height=13,wrap='word',state='disabled'); self.log.pack(fill='both',expand=True,pady=(10,0))
    def row_file(self,parent,label,var,command):
        g=ttk.Frame(parent); g.pack(fill='x',pady=7); ttk.Label(g,text=label,width=24).pack(side='left'); ttk.Entry(g,textvariable=var).pack(side='left',fill='x',expand=True); ttk.Button(g,text='Auswählen…',command=command).pack(side='left',padx=(8,0))
    def pick_pkg(self):
        p=filedialog.askopenfilename(filetypes=[('HistoScroll JSON','*.json'),('Alle Dateien','*.*')]);
        if p:self.pkg.set(p)
    def pick_out(self):
        p=filedialog.askdirectory();
        if p:self.out.set(p)
    def put(self,msg): self.q.put(('log',msg))
    def go(self):
        if not Path(self.pkg.get()).is_file(): return messagebox.showerror('HistoScroll','Bitte zuerst ein exportiertes Clip-Paket auswählen.')
        kinds=set();
        if self.editorial.get():kinds.add('editorial')
        if self.focus.get():kinds.add('focus')
        if self.excerpt.get():kinds.add('excerpt')
        if not kinds:return messagebox.showerror('HistoScroll','Wähle mindestens eine Clip-Art.')
        self.start.config(state='disabled'); self.bar.start(10); self.log.config(state='normal'); self.log.delete('1.0','end'); self.log.config(state='disabled')
        def work():
            try: generate_package(Path(self.pkg.get()),Path(self.out.get()),self.count.get(),self.voice.get(),self.rate.get(),kinds,self.put); self.q.put(('done',None))
            except Exception as e:self.q.put(('error',str(e)+'\n\n'+traceback.format_exc()))
        threading.Thread(target=work,daemon=True).start()
    def poll(self):
        try:
            while True:
                typ,msg=self.q.get_nowait()
                if typ=='log': self.log.config(state='normal');self.log.insert('end',msg+'\n');self.log.see('end');self.log.config(state='disabled')
                elif typ=='done': self.bar.stop();self.start.config(state='normal');messagebox.showinfo('HistoScroll','Fertig. Die MP4-Dateien und das Video-Manifest liegen im Ausgabeordner.')
                elif typ=='error': self.bar.stop();self.start.config(state='normal');messagebox.showerror('HistoScroll',msg)
        except queue.Empty: pass
        self.after(100,self.poll)
if __name__=='__main__': App().mainloop()
