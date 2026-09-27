import {config} from './config.js';

const SESSION_KEY='histoscroll-supabase-session-v1';
const trimSlash=s=>String(s||'').replace(/\/+$/,'');
const url=trimSlash(config.SUPABASE_URL);
const key=String(config.SUPABASE_PUBLISHABLE_KEY||'');
export const configured=()=>/^https:\/\/[^/]+\.supabase\.co$/i.test(url)&&key&& !/YOUR_|CHANGE_ME/i.test(key);
const encPath=p=>String(p).split('/').map(encodeURIComponent).join('/');
let session=null;

function parseError(body,status){
  const msg=body?.msg||body?.message||body?.error_description||body?.error||`HTTP ${status}`;
  if(/Invalid login credentials/i.test(msg))return 'E-Mail oder Passwort ist falsch.';
  if(/Email not confirmed/i.test(msg))return 'Bitte bestätige zuerst deine E-Mail-Adresse.';
  if(/User already registered/i.test(msg))return 'Für diese E-Mail existiert bereits ein Konto.';
  return String(msg);
}
async function raw(path,{method='GET',body,headers={},auth=true,parse='json'}={}){
  if(!configured())throw Error('Cloud-Speicher ist noch nicht eingerichtet. Trage Supabase URL und Publishable Key in public/config.js ein.');
  if(auth)await ensureSession();
  const h={'apikey':key,...headers};
  if(auth&&session?.access_token)h.Authorization='Bearer '+session.access_token;
  const r=await fetch(url+path,{method,body,headers:h});
  let data=null;
  if(parse==='blob')data=await r.blob();
  else if(parse==='text')data=await r.text();
  else {const t=await r.text();try{data=t?JSON.parse(t):null;}catch{data={message:t};}}
  if(!r.ok)throw Error(parseError(data,r.status));
  return data;
}
function persist(s){session=s||null;try{s?localStorage.setItem(SESSION_KEY,JSON.stringify(s)):localStorage.removeItem(SESSION_KEY);}catch{}}
function normalizeSession(s){if(!s?.access_token)return null;const expiresAt=s.expires_at||Math.floor(Date.now()/1000)+(Number(s.expires_in)||3600);return {...s,expires_at:expiresAt};}
export function currentSession(){return session;}
export function currentUser(){return session?.user||null;}
export async function requestOtp(email,displayName=''){
  await raw('/auth/v1/otp',{method:'POST',auth:false,headers:{'Content-Type':'application/json'},body:JSON.stringify({email,create_user:true,data:{display_name:displayName.trim()||undefined}})});
  return {ok:true};
}
export async function verifyOtp(email,token){
  const data=await raw('/auth/v1/verify',{method:'POST',auth:false,headers:{'Content-Type':'application/json'},body:JSON.stringify({email,token,type:'email'})});
  persist(normalizeSession(data));return session;
}
export async function refresh(){
  if(!session?.refresh_token)throw Error('Bitte melde dich erneut an.');
  const data=await raw('/auth/v1/token?grant_type=refresh_token',{method:'POST',auth:false,headers:{'Content-Type':'application/json'},body:JSON.stringify({refresh_token:session.refresh_token})});
  persist(normalizeSession(data));return session;
}
export async function ensureSession(){
  if(!session)throw Error('Bitte melde dich an.');
  if((session.expires_at||0)-Math.floor(Date.now()/1000)<90)await refresh();
  return session;
}
export async function restoreSession(){
  try{session=normalizeSession(JSON.parse(localStorage.getItem(SESSION_KEY)||'null'));}catch{session=null;}
  if(!session)return null;
  try{
    await ensureSession();
    const user=await raw('/auth/v1/user');
    session.user=user;persist(session);return session;
  }catch{persist(null);return null;}
}
export async function signOut(){
  try{if(session?.access_token)await raw('/auth/v1/logout',{method:'POST'});}catch{}
  persist(null);
}

const bucket=()=>config.BOOK_BUCKET||'book-packages';
const bookPath=(uid,id)=>`${uid}/${id}.json`;
async function db(path,options={}){return raw('/rest/v1/'+path,options);}
async function storage(path,options={}){return raw('/storage/v1/'+path,options);}
export async function isAdmin(){const u=currentUser();if(!u)return false;const rows=await db(`app_admins?user_id=eq.${encodeURIComponent(u.id)}&select=user_id&limit=1`);return !!rows?.length;}

export const books={
  async list(){
    const u=currentUser();if(!u)throw Error('Bitte melde dich an.');
    return db('books?select=id,title,author,edition,page_count,clip_count,generated_from,package_path,updated_at&order=updated_at.desc');
  },
  async get(id){
    const u=currentUser();if(!u)throw Error('Bitte melde dich an.');
    const rows=await db(`books?id=eq.${encodeURIComponent(id)}&select=package_path&limit=1`);
    if(!rows?.length)throw Error('Buch nicht gefunden.');
    const blob=await storage(`object/authenticated/${encodeURIComponent(bucket())}/${encPath(rows[0].package_path)}`,{parse:'blob'});
    const text=await blob.text();return JSON.parse(text);
  },
  async put(book){
    const u=currentUser();if(!u)throw Error('Bitte melde dich an.');
    const path=bookPath(u.id,book.id),blob=new Blob([JSON.stringify(book)],{type:'application/json'});
    if(blob.size>30_000_000)throw Error('Ein Buchpaket darf maximal 30 MB groß sein. Teile sehr große Bücher in mehrere Importe.');
    await storage(`object/${encodeURIComponent(bucket())}/${encPath(path)}`,{method:'POST',body:blob,headers:{'Content-Type':'application/json','x-upsert':'true'}});
    const row={user_id:u.id,id:book.id,title:String(book.title||'').slice(0,200),author:String(book.author||'Eigener Import').slice(0,200),edition:String(book.edition||'').slice(0,120),page_count:Number(book.pageCount)||0,clip_count:Array.isArray(book.clips)?book.clips.length:0,generated_from:String(book.generatedFrom||'').slice(0,100)||null,package_path:path,updated_at:new Date().toISOString()};
    await db('books?on_conflict=user_id,id',{method:'POST',body:JSON.stringify(row),headers:{'Content-Type':'application/json','Prefer':'resolution=merge-duplicates,return=minimal'}});
    return book;
  },
  async remove(id){
    const u=currentUser();if(!u)throw Error('Bitte melde dich an.');
    const rows=await db(`books?id=eq.${encodeURIComponent(id)}&select=package_path&limit=1`);
    if(rows?.[0]?.package_path)await storage(`object/${encodeURIComponent(bucket())}/${encPath(rows[0].package_path)}`,{method:'DELETE'}).catch(()=>{});
    await db(`books?id=eq.${encodeURIComponent(id)}`,{method:'DELETE',headers:{'Prefer':'return=minimal'}});
    return {ok:true};
  }
};

export const clipStates={
  async list(){
    const u=currentUser();if(!u)throw Error('Bitte melde dich an.');
    return db('clip_states?select=clip_id,book_id,seen,liked,favorite,last_seen_at,updated_at&order=updated_at.desc');
  },
  async put({clipId,bookId,seen=false,liked=false,favorite=false}){
    const u=currentUser();if(!u)throw Error('Bitte melde dich an.');
    const row={user_id:u.id,clip_id:String(clipId).slice(0,180),book_id:String(bookId||'').slice(0,120)||null,seen:!!seen,liked:!!liked,favorite:!!favorite,last_seen_at:seen?new Date().toISOString():null,updated_at:new Date().toISOString()};
    await db('clip_states?on_conflict=user_id,clip_id',{method:'POST',body:JSON.stringify(row),headers:{'Content-Type':'application/json','Prefer':'resolution=merge-duplicates,return=minimal'}});
    return row;
  }
};

export const media={
  enabled(){return /^https:\/\//i.test(String(config.PI_MEDIA_BASE_URL||''));},
  base(){return trimSlash(config.PI_MEDIA_BASE_URL);},
  async upload(file){
    if(!this.enabled())throw Error('Der optionale Pi-Medienserver ist noch nicht konfiguriert.');
    await ensureSession();
    const fd=new FormData();fd.append('file',file,file.name);
    const r=await fetch(this.base()+'/api/upload',{method:'POST',headers:{Authorization:'Bearer '+session.access_token},body:fd});
    const data=await r.json().catch(()=>({}));if(!r.ok)throw Error(data.detail||data.error||'Video-Upload fehlgeschlagen.');return data;
  },
  async signedUrl(mediaId){
    if(!this.enabled())throw Error('Der optionale Pi-Medienserver ist noch nicht konfiguriert.');
    await ensureSession();
    const r=await fetch(this.base()+'/api/sign/'+encodeURIComponent(mediaId),{headers:{Authorization:'Bearer '+session.access_token}});
    const data=await r.json().catch(()=>({}));if(!r.ok)throw Error(data.detail||data.error||'Video konnte nicht freigegeben werden.');return new URL(data.url,this.base()+'/').href;
  },
  async remove(mediaId){
    if(!this.enabled()||!mediaId)return;
    await ensureSession();
    const r=await fetch(this.base()+'/api/media/'+encodeURIComponent(mediaId),{method:'DELETE',headers:{Authorization:'Bearer '+session.access_token}});
    if(!r.ok&&r.status!==404){const data=await r.json().catch(()=>({}));throw Error(data.detail||data.error||'Video konnte nicht gelöscht werden.');}
  }
};
