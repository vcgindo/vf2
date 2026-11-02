import axios, { AxiosError } from 'axios';
import { createMtaPublicationBinding, PUBLICATION_HEADER, PUBLICATION_BOOTSTRAP } from './mta-publication-binding';

const A = 'a'.repeat(64), B = 'b'.repeat(64);
const lower = PUBLICATION_HEADER.toLowerCase();

const client = (bootstrap?: () => Promise<string>) => {
  const seen: any[] = [];
  let current = A;
  const transport = axios.create({ baseURL: 'http://localhost', adapter: async config => {
    seen.push(config);
    if (config.url?.endsWith(PUBLICATION_BOOTSTRAP)) {
      return { config, status: 200, statusText: 'OK', headers: {}, data: { mode: 'native', binding: bootstrap ? await bootstrap() : current } };
    }
    if (config.url?.endsWith('/AddRemark')) {
      current = B;
      return { config, status: 200, statusText: 'OK', headers: {}, data: { status: 200 } };
    }
    if (config.headers?.[PUBLICATION_HEADER] !== current) {
      throw new AxiosError('stale', 'ERR_BAD_REQUEST', config, undefined,
        { config, status: 409, statusText: 'Conflict', headers: {}, data: { error: 'publication_binding_missing_or_stale' } });
    }
    return { config, status: 200, statusText: 'OK', headers: { [lower]: current }, data: 'complete' };
  } });
  const binding = createMtaPublicationBinding(config => transport(config));
  transport.interceptors.request.use(binding.request);
  transport.interceptors.response.use(binding.response);
  return { transport, binding, seen, activate: () => { current = B; } };
};

test('concurrent first count/data share one bootstrap before either transport read', async () => {
  let finish!: (token: string) => void;
  const { transport, seen } = client(() => new Promise(resolve => { finish = resolve; }));
  const requests = Promise.all([transport.post('/api/mta/RRRDataCount'), transport.post('/api/mta/RRRData')]);
  await new Promise(resolve => setTimeout(resolve, 0));
  expect(seen).toHaveLength(1);
  expect(seen[0].url).toContain(PUBLICATION_BOOTSTRAP);
  finish(A);
  await requests;
  expect(seen.slice(1).map(c => c.headers[PUBLICATION_HEADER])).toEqual([A, A]);
});

test('count A cannot be followed by successful data/page/chart/export B', async () => {
  const { transport, seen, activate } = client();
  await transport.post('/api/mta/GetBTRDataCount');
  activate();
  for (const route of ['GetBTRData', 'RRRData', 'GetPlanningDataGraph', 'GetExportDataAsync', 'DownloadReports/LogisticPickListReport']) {
    await expect(transport.post('/api/mta/' + route, { paginationParameter: { pageNumber: 2 } },
      { responseType: route.includes('Export') ? 'blob' : 'json' })).rejects.toMatchObject({ response: { status: 409 } });
  }
  expect(seen.filter(c => c.url.endsWith(PUBLICATION_BOOTSTRAP))).toHaveLength(1);
  expect(seen.slice(1).every(c => c.headers[PUBLICATION_HEADER] === A)).toBe(true);
});

test('auth replay retains the original binding instead of bootstrapping B', async () => {
  const { transport, seen, activate } = client();
  const response = await transport.post('/api/mta/RRRData');
  activate();
  response.config.headers.Authorization = 'Bearer refreshed';
  await expect(transport(response.config)).rejects.toMatchObject({ response: { status: 409 } });
  expect(seen.filter(c => c.url.endsWith(PUBLICATION_BOOTSTRAP))).toHaveLength(1);
  expect(seen[seen.length - 1].headers[PUBLICATION_HEADER]).toBe(A);
});

test('stale or absent response assertion is rejected before caller receives data', async () => {
  const { binding } = client();
  for (const headers of [{}, { [lower]: B }]) {
    expect(() => binding.response({ config: { _mtaPublicationBinding: A }, headers, data: 'wrong' }))
      .toThrow('Publication response is missing or stale');
  }
});

test('metadata, initialized MDM, writes and MTO do not bootstrap or change', async () => {
  const send = jest.fn();
  const binding = createMtaPublicationBinding(send);
  for (const url of ['/api/mta/GetState', '/api/mta/GetMasterData', '/api/mta/DBMApplySelectedNorms',
    '/api/mta/AddRemark', '/api/mto/GetBTRData', PUBLICATION_BOOTSTRAP]) {
    const config = { url };
    expect(await binding.request(config)).toBe(config);
  }
  expect(send).not.toHaveBeenCalled();
});

test('successful mutation refreshes once and a superseded auth replay cannot adopt the new revision', async () => {
  const { transport, seen } = client();
  const original = await transport.post('/api/mta/RRRData');
  await transport.post('/api/mta/AddRemark', { data: [] });
  const fresh = await transport.post('/api/mta/RRRDataCount');
  expect(fresh.config.headers[PUBLICATION_HEADER]).toBe(B);
  expect(seen.filter(c => c.url.endsWith(PUBLICATION_BOOTSTRAP))).toHaveLength(2);
  await expect(transport(original.config)).rejects.toThrow('superseded');
  expect(seen.filter(c => c.url.endsWith('/AddRemark'))).toHaveLength(1);
});

test('late response and export from the previous refresh cannot be accepted', async () => {
  const { binding } = client();
  const config = await binding.request({ url: '/api/mta/GetExportDataAsync' });
  binding.refresh();
  expect(() => binding.response({ config, headers: { [lower]: A } })).toThrow('superseded');
  expect(binding.isCurrent({ config })).toBe(false);
});

test('failed bootstrap retries only on an explicit coordinated refresh', async () => {
  const send = jest.fn().mockRejectedValueOnce(new Error('unavailable'))
    .mockResolvedValue({ data: { mode: 'native', binding: B } });
  const binding = createMtaPublicationBinding(send);
  await expect(binding.request({ url: '/api/mta/RRRData' })).rejects.toThrow('unavailable');
  await expect(binding.request({ url: '/api/mta/RRRDataCount' })).rejects.toThrow('unavailable');
  expect(send).toHaveBeenCalledTimes(1);
  binding.refresh();
  const retried = await binding.request({ url: '/api/mta/RRRData' });
  expect(retried.headers[PUBLICATION_HEADER]).toBe(B);
  expect(send).toHaveBeenCalledTimes(2);
});

test('last-run date, count and grid share the explicit refresh binding', async () => {
  const {transport,binding,seen,activate}=client();
  await transport.get('/api/mta/GetLastRunDate');
  activate();binding.refresh();
  const results=await Promise.all([transport.get('/api/mta/GetLastRunDate'),
    transport.post('/api/mta/RRRDataCount'),transport.post('/api/mta/RRRData')]);
  expect(results.map(reply=>reply.config.headers[PUBLICATION_HEADER])).toEqual([B,B,B]);
  expect(seen.filter(c=>c.url.endsWith(PUBLICATION_BOOTSTRAP))).toHaveLength(2);
});

test('session invalidation does not notify metadata reads; explicit refresh unsubscribes cleanly', () => {
  const {binding}=client();const listener=jest.fn();const unsubscribe=binding.subscribeRefresh(listener);
  binding.refresh(false);expect(listener).not.toHaveBeenCalled();
  binding.refresh();expect(listener).toHaveBeenCalledTimes(1);
  unsubscribe();binding.refresh();expect(listener).toHaveBeenCalledTimes(1);
});
