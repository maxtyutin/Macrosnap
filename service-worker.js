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

// Fetch Event (Stale-While-Revalidate Strategy for assets, bypass for API requests)
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  
  // Bypass API requests or external resources that shouldn't be cached in the app shell
  if (url.pathname.startsWith('/api/') || event.request.method !== 'GET') {
    return; // Let browser handle it normally
  }
  
  // For other requests, apply Stale-While-Revalidate
  event.respondWith(
    caches.match(event.request).then(cachedResponse => {
      const fetchPromise = fetch(event.request).then(networkResponse => {
        // Cache the updated response if it's valid
        if (networkResponse && networkResponse.status === 200) {
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, networkResponse.clone());
          });
        }
        return networkResponse;
      }).catch(() => {
        // Fallback or ignore network error if offline
      });
      
      // Return cached response if available, else wait for network
      return cachedResponse || fetchPromise;
    })
  );
});
