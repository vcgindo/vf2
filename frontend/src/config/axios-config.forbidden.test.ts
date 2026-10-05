import axios from 'axios';
const { setupAxios } = jest.requireActual('./axios-config.tsx');
jest.mock('../helpers/utils', () => ({ cleanObject: (v: any) => v, loginRedirect: jest.fn() }));
jest.mock('../module-main/services/api', () => ({ MainService: {} }));
const originalLocation = window.location;
let redirect = jest.fn();
beforeEach(() => {
  jest.clearAllMocks();
  redirect = jest.fn();
  delete (window as any).location;
  (window as any).location = { pathname: '/mta/insights-and-trends/research-insights', set href(value: string) { redirect(value); } };
});
afterAll(() => { (window as any).location = originalLocation; });
const denied = { isAxiosError: true, code: 'ERR_BAD_REQUEST', config: { url: '/api/mta/GetAllReports' }, response: { status: 403, data: { message: 'denied' } } };
const handler = () => {
  const spy = jest.spyOn(axios.interceptors.response, 'use');
  setupAxios();
  return spy.mock.calls[spy.mock.calls.length - 1][1]!;
};
test('concurrent denials redirect once and preserve the denied response', async () => {
  const reject = handler();
  const replies = await Promise.all([reject(denied), reject(denied)]);
  expect(redirect).toHaveBeenCalledTimes(1);
  expect(redirect).toHaveBeenCalledWith('/permission-forbidden?URLPermission=true');
  for (const reply of replies) expect(reply).toMatchObject({ status: 403, response: denied.response.data });
});
test('a denied-page catalogue failure retains the page and denial', async () => {
  (window as any).location.pathname = '/permission-forbidden';
  const reply = await handler()(denied);
  expect(redirect).not.toHaveBeenCalled();
  expect(reply).toMatchObject({ status: 403, response: denied.response.data });
});
