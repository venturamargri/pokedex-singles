const CACHE_NAME = 'pokedex-singles-v7';
const assets = [
    '/pokedex-singles/', 
    '/pokedex-singles/index.html', 
    '/pokedex-singles/manifest.json'
];

// 1. Instalar y forzar que la nueva versión tome el control al instante
self.addEventListener('install', e => {
    e.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(assets))
    );
    self.skipWaiting(); 
});

// 2. Limpiar cachés antiguas para no ocupar memoria a lo tonto
self.addEventListener('activate', e => {
    e.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.map(key => {
                    if (key !== CACHE_NAME) return caches.delete(key);
                })
            );
        })
    );
    self.clients.claim();
});

// 3. Estrategia "Network First": Primero buscar en internet, si falla (sin conexión), usar caché
self.addEventListener('fetch', e => {
    e.respondWith(
        fetch(e.request)
            .then(response => {
                // Si hay internet, actualizamos la memoria guardada en silencio
                const resClone = response.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(e.request, resClone));
                return response;
            })
            .catch(() => {
                // Si estás offline, saca la versión guardada
                return caches.match(e.request);
            })
    );
});
