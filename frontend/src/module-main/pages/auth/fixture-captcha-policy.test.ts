import { fixtureCaptchaExempt } from './fixture-captcha-policy';

describe('local fixture CAPTCHA policy', () => {
  const original = window.location;
  beforeEach(() => {
    Object.defineProperty(window, 'location', { configurable: true,
      value: { origin: 'http://localhost:3006' } });
    global.fetch = jest.fn();
  });
  afterAll(() => Object.defineProperty(window, 'location', { value: original }));
  it('never consults the exception on protected or other origins', async () => {
    for (const port of [3002, 3003, 3004, 3005]) {
      Object.defineProperty(window, 'location', { value: { origin: `http://localhost:${port}` } });
      expect(await fixtureCaptchaExempt('stage2.broad@vectorflow.local')).toBe(false);
    }
    expect(fetch).not.toHaveBeenCalled();
  });
  it('accepts only an exact successful response and sends no password', async () => {
    (fetch as jest.Mock).mockResolvedValue({ status: 200, json: async () => ({ exempt: true }) });
    expect(await fixtureCaptchaExempt('stage2.broad@vectorflow.local')).toBe(true);
    expect(fetch).toHaveBeenCalledWith('/api/user/captcha-policy/', expect.objectContaining({
      method: 'POST', body: JSON.stringify({ email: 'stage2.broad@vectorflow.local' }),
      cache: 'no-store', credentials: 'omit',
    }));
  });
  it('denies errors, malformed responses and negative decisions', async () => {
    for (const result of [null, true, { exempt: 'true' }, { exempt: false }, { exempt: true, extra: 1 }]) {
      (fetch as jest.Mock).mockResolvedValue({ status: 200, json: async () => result });
      expect(await fixtureCaptchaExempt('fixture')).toBe(false);
    }
    (fetch as jest.Mock).mockResolvedValue({ status: 503 });
    expect(await fixtureCaptchaExempt('fixture')).toBe(false);
    (fetch as jest.Mock).mockRejectedValue(new Error('offline'));
    expect(await fixtureCaptchaExempt('fixture')).toBe(false);
  });
});
