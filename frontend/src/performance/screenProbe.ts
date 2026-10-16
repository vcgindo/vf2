import { useLayoutEffect } from 'react';

// Opt-in isolated acceptance instrumentation; no requests, credentials or data
// payloads are added or changed. Timings use browser events and rendered frames.
const enabled = process.env.REACT_APP_VF_SCREEN_PROBE === '1';
let installed = false;
let interaction = 0;
let sequence = 0;
let active: any;
const completed: any[] = [];
const pending = new Map<number, any>();
const startupRequests: any[] = [];

export function markStartup(name: string) {
    if (!enabled) return;
    const trace = (window as any).__VF_STARTUP_TRACE;
    if (trace && trace.marks.length < 120) trace.marks.push({ name, at: performance.now() });
}

export function traceRoute<T>(name: string, load: () => Promise<T>): Promise<T> {
    markStartup('route-request:' + name);
    return load().then(value => { markStartup('route-resolved:' + name); return value; });
}

markStartup('probe-module-evaluated');

function publish() {
    if (!enabled || !document.body) return;
    let node = document.getElementById('vf-performance-probe');
    if (!node) {
        node = document.createElement('output');
        node.id = 'vf-performance-probe';
        node.hidden = true;
        document.body.appendChild(node);
    }
    node.textContent = JSON.stringify({ active, completed, startup: (window as any).__VF_STARTUP_TRACE });
    node.setAttribute('data-status', active?.status || 'idle');
}

export function beginScreen(screen: string, action: string) {
    if (!enabled) return;
    const now = performance.now();
    const start = interaction || (action === 'navigation' && !active ? 0 : now);
    const requests = active ? Array.from(pending.values()) : startupRequests.slice();
    active = { epoch: ++sequence, screen, action, route: location.pathname,
        start, status: 'loading', rendered: false, visibilityAtStart: document.visibilityState, requests };
    publish();
}

export function useScreenProbe(screen: string) {
    useLayoutEffect(() => { beginScreen(screen, 'navigation'); }, [screen]);
}

function ready() {
    if (!active || !active.rendered || pending.size || active.status !== 'loading') return;
    const current = active;
    requestAnimationFrame(() => requestAnimationFrame(() => {
        if (active !== current || pending.size || current.status !== 'loading') return;
        if (!current.requests.length || current.requests.some((r: any) => {
            if (r.status > 0 && r.status < 400) return false;
            // Keep the original failure visible, but allow a successful retry of
            // that exact request to finish the measurement after token refresh.
            return !(r.status === 401 && current.requests.some((retry: any) =>
                retry.id === r.supersededBy && retry.retryOf === r.id &&
                retry.status > 0 && retry.status < 400));
        })) return;
        current.status = 'ready';
        current.elapsedMs = Math.round((performance.now() - current.start) * 100) / 100;
        current.readyAt = performance.timeOrigin + performance.now();
        current.visibilityAtReady = document.visibilityState;
        markStartup('usable:' + current.screen);
        const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
        current.navigation = navigation ? { responseEnd: navigation.responseEnd,
            domInteractive: navigation.domInteractive,
            domContentLoadedStart: navigation.domContentLoadedEventStart,
            domContentLoaded: navigation.domContentLoadedEventEnd, load: navigation.loadEventEnd } : null;
        current.resources = performance.getEntriesByType('resource')
            .filter((entry: any) => ['script', 'link', 'css', 'xmlhttprequest', 'fetch'].includes(entry.initiatorType))
            .map((entry: any) => ({ name: entry.name.split('?')[0], type: entry.initiatorType,
                start: entry.startTime, duration: entry.duration, requestStart: entry.requestStart,
                responseStart: entry.responseStart, responseEnd: entry.responseEnd,
                transferBytes: entry.transferSize, encodedBytes: entry.encodedBodySize,
                decodedBytes: entry.decodedBodySize, serverTiming: entry.serverTiming }));
        current.scripts = performance.getEntriesByType('resource')
            .filter((entry: any) => entry.initiatorType === 'script')
            .map((entry: any) => ({ name: entry.name.split('/').pop(), start: entry.startTime,
                duration: entry.duration, transferBytes: entry.transferSize,
                encodedBytes: entry.encodedBodySize, decodedBytes: entry.decodedBodySize }));
        const keys = current.requests.map((r: any) => r.key);
        current.duplicateRequests = keys.length - new Set(keys).size;
        completed.push(JSON.parse(JSON.stringify(current)));
        if (completed.length > 12) completed.shift();
        publish();
        console.info('[VF_SCREEN] ' + JSON.stringify(current));
    }));
}

export function screenRendered(screen: string) {
    if (!enabled || active?.screen !== screen) return;
    active.rendered = true;
    ready();
}

function fingerprint(value: string) {
    let hash = 2166136261;
    for (let i = 0; i < value.length; i++) hash = Math.imul(hash ^ value.charCodeAt(i), 16777619);
    return (hash >>> 0).toString(16);
}

export function installScreenProbe(client: any) {
    if (!enabled || installed) return;
    installed = true;
    document.addEventListener('click', () => { interaction = performance.now(); }, true);
    client.interceptors.request.use((config: any) => {
        const url = String(config.url || '');
        // Login/refresh payloads are never fingerprinted or recorded.
        if (!url.includes('/mta/') && !url.toLowerCase().includes('profile')) return config;
        const endpoint = url.split('?')[0];
        const key = String(config.method || 'get') + ':' + endpoint + ':' +
            fingerprint(JSON.stringify([config.params || {}, config.data || {}]));
        const item = { id: ++sequence, key, endpoint, start: performance.now(),
            initiator: active ? active.screen + ':' + active.action : 'shared-navigation', status: 0 };
        const previous = (active ? active.requests : startupRequests)
            .find((request: any) => request.id === config.vfProbeId);
        if (previous?.status === 401 && previous.key === key) {
            previous.supersededBy = item.id;
            (item as any).retryOf = previous.id;
        }
        config.vfProbeId = item.id;
        const trace = (window as any).__VF_STARTUP_TRACE;
        if (trace) {
            const correlationId = trace.id + '-' + item.id;
            config.headers = { ...config.headers, 'X-VF-Probe-ID': correlationId };
            (item as any).correlationId = correlationId;
        }
        pending.set(item.id, item);
        if (active) active.requests.push(item);
        else startupRequests.push(item);
        publish();
        return config;
    });
    const settle = (response: any, config: any, status: number) => {
        const item = pending.get(config?.vfProbeId);
        if (!item) return;
        item.durationMs = Math.round((performance.now() - item.start) * 100) / 100;
        item.status = status;
        item.serverTiming = response?.headers?.['server-timing'] || null;
        item.serverCorrelationId = response?.headers?.['x-vf-probe-id'] || null;
        item.bodyBytes = new TextEncoder().encode(JSON.stringify(response?.data ?? null)).length;
        pending.delete(item.id);
        publish();
        ready();
    };
    client.interceptors.response.use((response: any) => {
        settle(response, response.config, response.status);
        return response;
    }, (error: any) => {
        settle(error.response, error.config, error.response?.status || 599);
        return Promise.reject(error);
    });
}
