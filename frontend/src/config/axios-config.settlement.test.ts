import axios from 'axios';
import { setupAxios } from './axios-config';
import { MainService } from '../module-main/services/api';
import { REQUEST_TIMEOUT_MS, DOWNLOAD_TIMEOUT_MS } from '../helpers/requestDeadline';
import { PUBLICATION_HEADER, refreshMtaReportBinding, resetMtaReportBinding } from './mta-publication-binding';

jest.mock('axios', () => {
  const actual = jest.requireActual('axios');
  const client: any = jest.fn();
  client.defaults = {};
  client.interceptors = { request: { use: jest.fn() }, response: { use: jest.fn() } };
  return { __esModule: true, default: client, AxiosError: actual.AxiosError };
});
jest.mock('../performance/screenProbe', () => ({ installScreenProbe: jest.fn() }));
jest.mock('../helpers/utils', () => ({ cleanObject: (v: any) => v, loginRedirect: jest.fn() }));
jest.mock('../module-main/services/api', () => ({ MainService: {
  acquireToken: jest.fn(), refreshToken: jest.fn(),
  getLogoutUrl: () => '/logout', getrefreshTokenUrl: () => '/refresh',
} }));

const denied = (url: string, extra: any = {}) => ({
  isAxiosError: true, code: 'ERR_BAD_REQUEST',
  config: { url, headers: {}, ...extra },
  response: { status: 401, data: { code: 'token_not_valid' } },
});
const handlers = () => {
  setupAxios();
  const requests = (axios.interceptors.request.use as jest.Mock).mock.calls;
  const responses = (axios.interceptors.response.use as jest.Mock).mock.calls;
  return { request: requests[requests.length - 1][0], reject: responses[responses.length - 1][1] };
};
beforeEach(() => { jest.clearAllMocks(); (axios as unknown as jest.Mock).mockResolvedValue({ status: 200 }); });

test('actual error interceptor retains acquisition refusal and bootstraps only next explicit refresh', async () => {
  resetMtaReportBinding();
  const date={status:200,data:[{formatted:'19 Oct 2026',rawDate:'2026-10-19'}]};
  (axios as unknown as jest.Mock).mockResolvedValue({data:{mode:'native',binding:'a'.repeat(64),date_response:date,report_acquisition:true}});
  const {request,reject}=handlers();
  await request({url:'/api/mta/GetLastRunDate',headers:{}});
  refreshMtaReportBinding();
  const original=await request({url:'/api/mta/GetBPRData',headers:{}});
  expect(original.headers[PUBLICATION_HEADER]).toBe('acquire');
  await expect(reject({isAxiosError:true,config:original,response:{status:409,data:{error:'publication_binding_missing_or_stale'}}})).rejects.toMatchObject({status:409});
  expect(axios).toHaveBeenCalledTimes(1);
  refreshMtaReportBinding();
  expect((await request({url:'/api/mta/GetBPRData',headers:{}})).headers[PUBLICATION_HEADER]).toBe('a'.repeat(64));
  expect(axios).toHaveBeenCalledTimes(2);
  expect(MainService.refreshToken).not.toHaveBeenCalled();
  resetMtaReportBinding();
});

test('ordinary requests and downloads have finite distinct deadlines', async () => {
  const { request } = handlers();
  expect(axios.defaults.timeout).toBe(REQUEST_TIMEOUT_MS);
  const download = await request({ url: '/download', headers: {}, responseType: 'blob', timeout: REQUEST_TIMEOUT_MS });
  expect(download.timeout).toBe(DOWNLOAD_TIMEOUT_MS);
  expect((await request({ url: '/custom', headers: {}, responseType: 'blob', timeout: 1234 })).timeout).toBe(1234);
});

test('failed refresh rejects every waiter without replaying a business request', async () => {
  let fail!: (error: Error) => void;
  (MainService.refreshToken as jest.Mock).mockReturnValue(new Promise((resolve, reject) => { fail = reject; }));
  const { reject } = handlers();
  const first = reject(denied('/one'));
  const second = reject(denied('/two'));
  const settled = Promise.allSettled([first, second]);
  const failure = new Error('refresh unavailable'); fail(failure);
  expect(await settled).toEqual([{ status: 'rejected', reason: failure }, { status: 'rejected', reason: failure }]);
  expect(MainService.refreshToken).toHaveBeenCalledTimes(1);
  expect(axios).not.toHaveBeenCalled();
});

test('cookie-only refresh releases waiters without Bearer undefined', async () => {
  let finish!: (value: undefined) => void;
  (MainService.refreshToken as jest.Mock).mockReturnValue(new Promise(resolve => { finish = resolve; }));
  const { reject } = handlers();
  const a = denied('/one'), b = denied('/two');
  const replies = Promise.all([reject(a), reject(b)]);
  finish(undefined);
  expect(await replies).toEqual([{ status: 200 }, { status: 200 }]);
  expect(a.config.headers).not.toHaveProperty('Authorization');
  expect(b.config.headers).not.toHaveProperty('Authorization');
  expect(b.config).toHaveProperty('_retry', true);
});

test('resolved form400 contract remains distinct from timeout rejection', async () => {
  const { reject } = handlers();
  const validation = { isAxiosError: true, code: 'ERR_BAD_REQUEST', config: { url: '/form' }, response: { status: 400, data: { message: 'invalid value' } } };
  expect(await reject(validation)).toMatchObject({ status: 400, message: 'invalid value' });
  await expect(reject({ isAxiosError: true, code: 'ECONNABORTED', config: { url: '/grid' } })).rejects.toMatchObject({ message: 'The request timed out. Check its result or status before trying again.' });
});

test('logout opt-out does not start another refresh cycle', async () => {
  await expect(handlers().reject(denied('/logout', { _skipAuthRefresh: true }))).rejects.toMatchObject({ status: 401 });
  expect(MainService.refreshToken).not.toHaveBeenCalled();
});

test('a slow replay cannot clear or reject a later refresh generation', async () => {
  let finishA!: (value: undefined) => void, finishB!: (value: undefined) => void;
  let failReplayA!: (error: Error) => void;
  (MainService.refreshToken as jest.Mock)
    .mockReturnValueOnce(new Promise(resolve => { finishA = resolve; }))
    .mockReturnValueOnce(new Promise(resolve => { finishB = resolve; }));
  (axios as unknown as jest.Mock).mockReturnValueOnce(new Promise((resolve, reject) => { failReplayA = reject; }));
  const { reject } = handlers();
  const a = reject(denied('/a'));
  const caughtA = a.catch((error: Error) => error);
  finishA(undefined);
  await Promise.resolve();
  expect(axios).toHaveBeenCalledTimes(1);
  const b = reject(denied('/b')), c = reject(denied('/c'));
  const replayFailure = new Error('a replay failed');
  failReplayA(replayFailure);
  expect(await caughtA).toBe(replayFailure);
  const d = reject(denied('/d'));
  expect(MainService.refreshToken).toHaveBeenCalledTimes(2);
  finishB(undefined);
  expect(await Promise.all([b, c, d])).toEqual([{ status: 200 }, { status: 200 }, { status: 200 }]);
});


test('missing refresh cookie rejects immediately even while another refresh is pending', async () => {
  let finish!: (value: undefined) => void;
  (MainService.refreshToken as jest.Mock).mockReturnValue(new Promise(resolve => { finish = resolve; }));
  const { reject } = handlers();
  const leader = reject(denied('/grid'));
  const missing = { ...denied('/refresh'), response: { status: 401, data: { error: 'Refresh token missing' } } };
  await expect(reject(missing)).rejects.toMatchObject({ status: 401, error: 'Refresh token missing' });
  expect(MainService.refreshToken).toHaveBeenCalledTimes(1);
  finish(undefined);
  await leader;
});

test('401 refresh replays a real bound MTA request with its original publication', async () => {
  const token = 'a'.repeat(64);
  (axios as unknown as jest.Mock).mockResolvedValueOnce({ data: { mode: 'native', binding: token } });
  (MainService.refreshToken as jest.Mock).mockResolvedValue({ access: 'renewed-access' });
  const { request, reject } = handlers();
  const original = await request({ url: '/api/mta/RRRData', headers: {} });
  expect(original.headers[PUBLICATION_HEADER]).toBe(token);
  await reject({ ...denied(original.url), config: original });
  const replay = (axios as unknown as jest.Mock).mock.calls[1][0];
  expect(replay.headers[PUBLICATION_HEADER]).toBe(token);
  expect(replay.headers.Authorization).toBe('Bearer renewed-access');
  expect((axios as unknown as jest.Mock).mock.calls).toHaveLength(2);
});

test.each([401, 403, 400])('superseded report %s is rejected before refresh, redirect or resolved validation handling', async status => {
  refreshMtaReportBinding();
  (axios as unknown as jest.Mock).mockResolvedValueOnce({ data: { mode: 'native', binding: 'a'.repeat(64) } });
  const { request, reject } = handlers();
  const original = await request({ url: '/api/mta/RRRData', headers: {} });
  refreshMtaReportBinding();
  await expect(reject({ ...denied(original.url), config: original,
    response: { status, data: { detail: 'obsolete response' } } })).rejects.toThrow('superseded');
  expect(MainService.refreshToken).not.toHaveBeenCalled();
  expect(axios).toHaveBeenCalledTimes(1);
});
