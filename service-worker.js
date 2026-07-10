const CACHE_NAME = 'macrosnap-cache-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/styles.css',
  '/app.js',
  '/manifest.json',
  '/images/avocado_toast.jpg',
  '/images/berry_bowl.jpg',
  '/images/chicken_salad.jpg',
  '/images/pepperoni_pizza.jpg',
  '/images/icon-192.png',
  '/images/icon-512.png',
  '/images/apple-touch-icon.png'
];

// Install Event
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[Service Worker] Caching app shell assets');
        return cache.addAll(ASSETS_TO_CACHE);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate Event
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            console.log('[Service Worker] Clearing old cache:', cache);
            return caches.delete(cache);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event (Stale-While-Revalidate Strategy for same-origin assets, direct fetch for cross-origin or API)
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  
  // Only handle GET requests for same-origin resources
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }
  
  // Bypass API requests
  if (url.pathname.startsWith('/api/')) {
    return;
  }
  
  event.respondWith(
    caches.match(event.request).then(cachedResponse => {
      if (cachedResponse) {
        // Fetch fresh copy in background to update the cache
        fetch(event.request).then(networkResponse => {
          if (networkResponse && networkResponse.status === 200) {
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, networkResponse.clone());
            });
          }
        }).catch(() => {
          // Ignore background fetch failures
        });
        return cachedResponse;
      }
      
      // Fetch from network normally (letting errors propagate naturally)
      return fetch(event.request);
    })
  );
});
