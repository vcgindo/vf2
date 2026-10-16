export {};

describe('screen measurement across existing token refresh', () => {
    let request: any, success: any, failure: any, probe: any;
    let frames: Array<FrameRequestCallback>;
    let originalFlag: string | undefined;

    beforeEach(() => {
        jest.resetModules();
        originalFlag = process.env.REACT_APP_VF_SCREEN_PROBE;
        process.env.REACT_APP_VF_SCREEN_PROBE = '1';
        document.body.innerHTML = '';
        frames = [];
        window.requestAnimationFrame = jest.fn(callback => { frames.push(callback); return frames.length; });
        Object.defineProperty(performance, 'getEntriesByType', { configurable: true, value: () => [] });
        (global as any).TextEncoder = require('util').TextEncoder;
        jest.spyOn(console, 'info').mockImplementation(() => {});
        probe = require('./screenProbe');
        probe.installScreenProbe({ interceptors: {
            request: { use: (callback: any) => { request = callback; } },
            response: { use: (ok: any, bad: any) => { success = ok; failure = bad; } }
        } });
    });

    afterEach(() => {
        process.env.REACT_APP_VF_SCREEN_PROBE = originalFlag;
        jest.restoreAllMocks();
    });

    const read = () => JSON.parse(document.getElementById('vf-performance-probe')!.textContent!);
    const render = () => {
        probe.screenRendered('Planning');
        while (frames.length) frames.shift()!(0);
    };
    const reject = async (config: any, status: number) => {
        const error = { config, response: { status, data: {} } };
        await expect(failure(error)).rejects.toBe(error);
    };
    const resolve = (config: any) => {
        const response = { config, status: 200, data: { value: 6 } };
        expect(success(response)).toBe(response);
    };

    test('startup 401 and successful same-request retry retain both receipts and become ready', async () => {
        const config = request({ url: '/api/profile/', method: 'get' });
        await reject(config, 401);
        request(config);
        resolve(config);
        probe.beginScreen('Planning', 'navigation');
        render();
        const result = read().active;
        expect(result.status).toBe('ready');
        expect(result.requests.map((r: any) => r.status)).toEqual([401, 200]);
        expect(result.requests[0].supersededBy).toBe(result.requests[1].id);
        expect(result.duplicateRequests).toBe(1);
    });

    test('queued retry without _retry also completes within an active screen', async () => {
        probe.beginScreen('Planning', 'navigation');
        const config = request({ url: '/api/mta/GetPlanningDataCount', method: 'post', data: { date: '2026-07-07' } });
        await reject(config, 401);
        request(config);
        render();
        expect(read().active.status).toBe('loading');
        resolve(config);
        render();
        expect(read().active.status).toBe('ready');
    });

    test.each([401, 403, 500])('failed retry %s never becomes ready', async status => {
        probe.beginScreen('Planning', 'navigation');
        const config = request({ url: '/api/profile/', method: 'get' });
        await reject(config, 401);
        request(config);
        await reject(config, status);
        render();
        expect(read().active.status).toBe('loading');
    });

    test('unrelated successful request cannot conceal a denied request', async () => {
        probe.beginScreen('Planning', 'navigation');
        const config = request({ url: '/api/mta/report', method: 'post', data: { location: 'one' } });
        await reject(config, 401);
        config.data = { location: 'two' };
        request(config);
        resolve(config);
        render();
        expect(read().active.status).toBe('loading');
        expect(read().active.requests[0].supersededBy).toBeUndefined();
    });
});
