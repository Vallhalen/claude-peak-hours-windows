/**
 * Service Worker for Claude Peak Hours PWA + Windows Widget.
 */

// Import shared peak hours logic
importScripts('peak-hours.js');

const CACHE_NAME = 'claude-peak-hours-v1';
const ASSETS = [
    './',
    './index.html',
    './peak-hours.js',
    './manifest.json',
    './icons/icon-192.png',
    './icons/icon-512.png',
];

// ---------------------------------------------------------------------------
// Standard PWA lifecycle
// ---------------------------------------------------------------------------

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
});

// ---------------------------------------------------------------------------
// Widget data helper
// ---------------------------------------------------------------------------

function getWidgetData() {
    const state = getPeakState();
    const isPolish = true; // Default to Polish for the widget

    const statusIcon = state.status === 'off-peak'
        ? 'https://vallhalen.github.io/claude-peak-hours-windows/icons/dot-green.png'
        : state.status === 'peak'
            ? 'https://vallhalen.github.io/claude-peak-hours-windows/icons/dot-red.png'
            : 'https://vallhalen.github.io/claude-peak-hours-windows/icons/dot-yellow.png';

    return {
        statusIcon,
        statusTitle: isPolish
            ? (state.isPeak ? 'ZWIĘKSZONE ZUŻYCIE' : 'PEŁNA MOC')
            : (state.isPeak ? 'HIGHER USAGE' : 'FULL POWER'),
        statusColor: state.status === 'off-peak' ? 'Good' : state.status === 'peak' ? 'Attention' : 'Warning',
        statusDescription: isPolish
            ? (state.isPeak ? 'Limity zużywają się szybciej' : 'Claude działa na full — korzystaj!')
            : (state.isPeak ? 'Limits consumed faster' : 'Claude at full capacity — go ahead!'),
        nextChangeLabel: isPolish
            ? (state.isPeak ? 'Pełna moc za' : 'Ograniczenia za')
            : (state.isPeak ? 'Full power in' : 'Higher usage in'),
        countdown: state.countdownText,
        peakHoursLocal: state.peakHoursLocal,
        workdaysLabel: isPolish ? 'Dni robocze' : 'Workdays',
        workdaysValue: isPolish ? 'Pon–Pt' : 'Mon–Fri',
    };
}

// ---------------------------------------------------------------------------
// Windows Widget events (PWA Widget API)
// ---------------------------------------------------------------------------

self.addEventListener('widgetinstall', (event) => {
    event.waitUntil(updateWidget(event.widget));
});

self.addEventListener('widgetresume', (event) => {
    event.waitUntil(updateWidget(event.widget));
});

self.addEventListener('widgetclick', (event) => {
    // Open the PWA when widget is clicked
    event.waitUntil(
        clients.openWindow('/').then(() => updateWidget(event.widget))
    );
});

self.addEventListener('widgetuninstall', (event) => {
    // Nothing to clean up
});

async function updateWidget(widget) {
    try {
        const templateResponse = await fetch('./widget/template.json');
        const template = await templateResponse.text();
        const data = JSON.stringify(getWidgetData());

        await self.widgets.updateByTag('peak-status', { template, data });
    } catch (e) {
        console.error('Widget update failed:', e);
    }
}

// Periodic widget update (called by the system based on manifest "update" interval)
self.addEventListener('periodicsync', (event) => {
    if (event.tag === 'widget-update') {
        event.waitUntil(
            self.widgets.getByTag('peak-status').then((widget) => {
                if (widget) return updateWidget(widget);
            })
        );
    }
});
