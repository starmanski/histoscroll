const CACHE='histoscroll-pages-v9';
const SHELL=['./','./index.html','./style.css','./app.js','./core.js','./cloud.js','./favicon.svg','./manifest.webmanifest','./icons/icon-192.png','./icons/icon-512.png','./icons/icon-maskable-512.png','./icons/apple-touch-icon.png'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
 const req=event.request,url=new URL(req.url);
 if(req.method!=='GET'||url.origin!==self.location.origin)return;
 if(url.pathname.endsWith('/config.js')){event.respondWith(fetch(req).catch(()=>caches.match(req)));return;}
 if(req.mode==='navigate'){
  event.respondWith(fetch(req).then(r=>{const copy=r.clone();caches.open(CACHE).then(c=>c.put(new URL('./index.html',self.registration.scope),copy));return r;}).catch(()=>caches.match(new URL('./index.html',self.registration.scope))));
  return;
 }
 event.respondWith(caches.match(req).then(cached=>{
  const network=fetch(req).then(r=>{if(r.ok){const copy=r.clone();caches.open(CACHE).then(c=>c.put(req,copy));}return r;}).catch(()=>cached);
  return cached||network;
 }));
});
