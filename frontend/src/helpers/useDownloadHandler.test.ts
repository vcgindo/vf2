// DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
// Direct human exception: only MTA download transport and its focused proof.
import axios, { AxiosError } from 'axios';
import useDownloadHandler from './useDownloadHandler';
import { setupAxios } from '../config/axios-config';
import { MainService } from '../module-main/services/api';
import { notifyError } from './notify';

jest.mock('./notify', () => ({ notifyError: jest.fn() }));
jest.mock('../VectorFlow/Pages/MTO/Common/encryption', () => ({ decryptStorageData: jest.fn(async () => null) }));
jest.mock('../module-main/services/api', () => ({ MainService: {
  acquireToken: jest.fn(), refreshToken: jest.fn(), getrefreshTokenUrl: () => '/refresh', getLogoutUrl: () => '/logout'
} }));
jest.mock('./utils', () => ({ cleanObject: (v: unknown) => v, loginRedirect: jest.fn() }));
jest.mock('../performance/screenProbe', () => ({ installScreenProbe: jest.fn() }));

const originalAdapter = axios.defaults.adapter;
let clicked: jest.SpyInstance;
beforeEach(() => {
  jest.clearAllMocks();
  process.env.REACT_APP_API_HOST = '/';
  axios.interceptors.request.clear();
  axios.interceptors.response.clear();
  setupAxios();
  (MainService.acquireToken as jest.Mock).mockResolvedValue({ access: 'test-access' });
  (MainService.refreshToken as jest.Mock).mockResolvedValue({ access: 'test-refreshed' });
  window.history.replaceState({}, '', '/permission-forbidden');
  URL.createObjectURL = jest.fn(() => 'blob:test-download');
  URL.revokeObjectURL = jest.fn();
  clicked = jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  jest.spyOn(console, 'log').mockImplementation(() => {});
});
afterEach(() => {
  axios.defaults.adapter = originalAdapter;
  document.querySelectorAll('a[download]').forEach(e => e.remove());
  jest.restoreAllMocks();
});
const denied = (config: any, status: number) => new AxiosError('Denied', 'ERR_BAD_REQUEST', config, null, {
  status, statusText: 'Denied', headers: {}, config, data: { detail: 'Invalid token', code: 'token_not_valid' }
});

test('MTA download carries the real existing Axios authorization and keeps bytes/name', async () => {
  const bytes = new Blob(['a,b\n1,2\n'], { type: 'text/csv' });
  axios.defaults.adapter = async config => {
    expect(config.headers.Authorization).toBe('Bearer test-access');
    expect(config.responseType).toBe('blob');
    expect(config.url).toContain('/api/mta/DownloadReports/Input%20Data');
    return { data: bytes, status: 200, statusText: 'OK', headers: {}, config };
  };
  expect(await useDownloadHandler().handleDownloadVF('Input Data', 'input.csv')).toBe(true);
  expect(URL.createObjectURL).toHaveBeenCalledWith(bytes);
  expect(clicked).toHaveBeenCalledTimes(1);
  expect(document.querySelector('a[download]')).toHaveAttribute('download', 'input.csv');
  expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:test-download');
  expect(notifyError).not.toHaveBeenCalled();
});

test('MTA download uses existing refresh once after an expired-token response', async () => {
  let calls = 0;
  axios.defaults.adapter = async config => {
    if (++calls === 1) throw denied(config, 401);
    expect(config.headers.Authorization).toBe('Bearer test-refreshed');
    return { data: new Blob(['ok']), status: 200, statusText: 'OK', headers: {}, config };
  };
  expect(await useDownloadHandler().handleDownloadVF('InputData', '')).toBe(true);
  expect(MainService.refreshToken).toHaveBeenCalledTimes(1);
  expect(document.querySelector('a[download]')).toHaveAttribute('download', 'ReportFile.zip');
});

test.each([403, 404])('MTA download fails closed for %s without a file', async status => {
  axios.defaults.adapter = async config => { throw denied(config, status); };
  expect(await useDownloadHandler().handleDownloadVF('InputData', 'input.csv')).toBe(false);
  expect(clicked).not.toHaveBeenCalled();
  expect(URL.createObjectURL).not.toHaveBeenCalled();
  expect(notifyError).toHaveBeenCalledWith(status === 404 ? 'File not found' : 'Error while downloading');
});
