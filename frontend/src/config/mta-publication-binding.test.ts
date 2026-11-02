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

test('date and report pair share bootstrap; the date causes no second HTTP request', async () => {
  const date = {status:200, data:[{formatted:'19 Oct 2026',rawDate:'2026-10-19'}]};
  const send = jest.fn().mockResolvedValue({data:{mode:'native',binding:A,date_response:date}});
  const binding = createMtaPublicationBinding(send);
  const network = jest.fn(async config => ({config,status:200,statusText:'OK',headers:{[lower]:A},data:'grid'}));
  const transport = axios.create({baseURL:'http://localhost',adapter:network});
  transport.interceptors.request.use(binding.request);
  transport.interceptors.response.use(binding.response);
  const results = await Promise.all([transport.get('/api/mta/GetLastRunDate'),
    transport.post('/api/mta/GetBTRDataCount'),transport.post('/api/mta/GetBTRData')]);
  expect(send).toHaveBeenCalledTimes(1);
  expect(network.mock.calls.map(call=>call[0].url)).toEqual(['/api/mta/GetBTRDataCount','/api/mta/GetBTRData']);
  expect(results[0].data).toEqual(date);
  expect(results.map(r=>r.config.headers[PUBLICATION_HEADER])).toEqual([A,A,A]);
  results[0].data.data[0].rawDate='modified-by-consumer';
  expect((await transport.get('/api/mta/GetLastRunDate')).data).toEqual(date);
});

test('piggyback date cannot survive a superseded refresh and cannot silently fall back when malformed', async () => {
  let complete!: (value:any)=>void;
  const send=jest.fn(()=>new Promise(resolve=>{complete=resolve;}));
  const binding=createMtaPublicationBinding(send);
  const pending=binding.request({url:'/api/mta/GetLastRunDate'});
  binding.refresh();
  complete({data:{mode:'native',binding:A,date_response:{status:200,data:[{formatted:'old',rawDate:'2026-10-19'}]}}});
  await expect(pending).rejects.toThrow('superseded');
  const malformed=createMtaPublicationBinding(async()=>({data:{mode:'native',binding:B,date_response:{status:200,data:[]}}}));
  await expect(malformed.request({url:'/api/mta/GetLastRunDate'})).rejects.toThrow('date is unavailable');
});

test('ordinary legacy and old-server date reads retain their network adapter', async () => {
  for(const data of [{mode:'legacy',binding:null},{mode:'native',binding:A}]){
    const binding=createMtaPublicationBinding(async()=>({data}));
    const adapter=jest.fn();
    const config=await binding.request({url:'/api/mta/GetLastRunDate',adapter});
    expect(config.adapter).toBe(adapter);
  }
});

test('a date array cannot pass string validation through regex coercion', async () => {
  const binding=createMtaPublicationBinding(async()=>({data:{mode:'native',binding:A,
    date_response:{status:200,data:[{formatted:'19 Oct 2026',rawDate:['2026-10-19']}]}}}));
  await expect(binding.request({url:'/api/mta/GetLastRunDate'})).rejects.toThrow('date is unavailable');
});
const nativeDate = {status:200,recordCount:null,data:[{formatted:'19 Oct 2026',rawDate:'2026-10-19'}]};
const dateHeader = 'x-vectorflow-publication-date';
const fastClient = async () => {
  const send = jest.fn().mockResolvedValue({data:{mode:'native',binding:A,date_response:nativeDate,report_acquisition:true}});
  const binding = createMtaPublicationBinding(send);
  await binding.request({url:'/api/mta/GetLastRunDate'});
  binding.refresh(true,true);
  const reply = (config:any, token=A, date:any=nativeDate, extra:any={}) => binding.response({
    config,status:200,headers:{[lower]:token,[dateHeader]:JSON.stringify(date)},data:{status:200},...extra,
  });
  return {binding,send,reply};
};

test('acquisition refusal rediscovers scoped capability only on explicit refresh, ignoring old errors', async () => {
  const {binding,send,reply}=await fastClient();
  const requests=await Promise.all(['GetBPRDataCount','GetBPRData'].map(name=>binding.request({url:'/api/mta/'+name,method:'post'})));
  const refusal=(config:any)=>({config,response:{status:409,data:{error:'publication_binding_missing_or_stale'}}});
  reply(requests[0]); // A successful companion must never be repinned by recovery.
  binding.refused(refusal(requests[1]));
  expect(binding.dateFromReports()).toBe(true);
  expect((await binding.request({url:'/api/mta/GetBPRData'})).headers[PUBLICATION_HEADER]).toBe(A);
  expect(send).toHaveBeenCalledTimes(1); // No automatic bootstrap or replay.
  const scopedDate={status:200,data:[{formatted:'20 Oct 2026',rawDate:'2026-10-20'}]};
  send.mockResolvedValueOnce({data:{mode:'native',binding:B,date_response:scopedDate,report_acquisition:false}});
  binding.refresh(true,true);
  expect(binding.dateFromReports()).toBe(false);
  const recovered=await Promise.all(['GetBPRDataCount','GetBPRData','GetLastRunDate'].map(name=>binding.request({url:'/api/mta/'+name})));
  expect(recovered.map(c=>c.headers[PUBLICATION_HEADER])).toEqual([B,B,B]);
  expect((await recovered[2].adapter(recovered[2])).data).toEqual(scopedDate);
  expect(send).toHaveBeenCalledTimes(2);
  // Rediscover Full normally; an old scoped refusal cannot disable its next refresh.
  binding.refresh();
  await binding.request({url:'/api/mta/GetLastRunDate'});
  binding.refused(refusal(requests[1]));
  binding.refresh(true,true);
  expect(binding.dateFromReports()).toBe(true);
  expect((await binding.request({url:'/api/mta/GetBTRData'})).headers[PUBLICATION_HEADER]).toBe('acquire');
});

test.each([false,true])('matching acquisition companions pin once in either response order (%s)',async reverse=>{
  const {binding,send,reply}=await fastClient(); const dates=jest.fn();binding.subscribeDate(dates);
  const requests=await Promise.all(['GetBTRDataCount','GetBTRData'].map(name=>binding.request({url:'/api/mta/'+name})));
  expect(requests.map(r=>r.headers[PUBLICATION_HEADER])).toEqual(['acquire','acquire']);
  if(reverse)requests.reverse(); requests.forEach(config=>reply(config));
  expect(dates).toHaveBeenCalledTimes(1);expect(send).toHaveBeenCalledTimes(1);
  expect((await binding.request({url:'/api/mta/GetPlanningDataGraph'})).headers[PUBLICATION_HEADER]).toBe(A);
});

test.each([false,true])('conflicting acquisition companions never replace first pin (%s)',async reverse=>{
  const {binding,reply}=await fastClient();const dates=jest.fn();binding.subscribeDate(dates);
  const requests=await Promise.all(['GetBTRDataCount','GetBTRData'].map(name=>binding.request({url:'/api/mta/'+name})));
  if(reverse)requests.reverse(); reply(requests[0],A);
  expect(()=>reply(requests[1],B)).toThrow('binding changed');
  expect(dates).toHaveBeenCalledTimes(1);
  expect((await binding.request({url:'/api/mta/GetBTRData'})).headers[PUBLICATION_HEADER]).toBe(A);
});

test.each([false,true])('bootstrap export and report acquisition share immutable pin (%s)',async bootstrapFirst=>{
  const {binding,send,reply}=await fastClient();
  const report=await binding.request({url:'/api/mta/GetBTRData'});
  let finish!:(response:any)=>void;send.mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
  const exporting=binding.request({url:'/api/mta/GetExportDataAsync'});
  const bootstrap={data:{mode:'native',binding:B,date_response:nativeDate,report_acquisition:true}};
  if(bootstrapFirst){finish(bootstrap);await exporting;expect(()=>reply(report,A)).toThrow('binding changed');}
  else {reply(report,A);finish(bootstrap);await expect(exporting).rejects.toThrow('binding changed');}
});

test.each([
  {status:500},{data:{status:400}},{headers:{}},
  {headers:{[lower]:B,[dateHeader]:'bad-json'}},
  {headers:{[lower]:B,[dateHeader]:JSON.stringify({...nativeDate,data:[{formatted:'x',rawDate:['2026-10-19']}]})}},
])('failed/malformed acquisition cannot pin or publish date %#',async extra=>{
  const {binding,reply}=await fastClient();const dates=jest.fn();binding.subscribeDate(dates);
  const failed=await binding.request({url:'/api/mta/GetBTRDataCount'});
  expect(()=>reply(failed,B,nativeDate,extra)).toThrow();expect(dates).not.toHaveBeenCalled();
  const valid=await binding.request({url:'/api/mta/GetBTRData'});expect(valid.headers[PUBLICATION_HEADER]).toBe('acquire');
  reply(valid,A);expect(dates).toHaveBeenCalledTimes(1);
});

test('same token cannot introduce conflicting date envelope',async()=>{
 const {binding,reply}=await fastClient();const a=await binding.request({url:'/api/mta/GetBTRDataCount'});
 const b=await binding.request({url:'/api/mta/GetBTRData'});reply(a);
 expect(()=>reply(b,A,{...nativeDate,data:[{formatted:'20 Oct 2026',rawDate:'2026-10-20'}]})).toThrow('binding changed');
});

test('auth replay adopts companion pin, but explicit tokens and superseded epochs never change',async()=>{
 const {binding,reply}=await fastClient();const retry=await binding.request({url:'/api/mta/GetBTRData'});
 const companion=await binding.request({url:'/api/mta/GetBTRDataCount'});reply(companion,A);
 expect((await binding.request(retry)).headers[PUBLICATION_HEADER]).toBe(A);
 await expect(binding.request({url:'/api/mta/GetBTRData',headers:{[PUBLICATION_HEADER]:B}})).rejects.toThrow('binding changed');
 binding.refresh(true,true);await expect(binding.request(retry)).rejects.toThrow('superseded');
 expect(()=>reply(companion)).toThrow('superseded');
});

test('session reset and mutation refresh clear fast mode; only explicit capable refresh acquires',async()=>{
 const {binding,send}=await fastClient();expect(binding.dateFromReports()).toBe(true);
 binding.refresh();expect(binding.dateFromReports()).toBe(false);
 await binding.request({url:'/api/mta/GetBTRData'});expect(send).toHaveBeenCalledTimes(2);
 binding.refresh(false);binding.refresh(true,true);expect(binding.dateFromReports()).toBe(false);
 await binding.request({url:'/api/mta/GetBTRData'});expect(send).toHaveBeenCalledTimes(3);
});

test('real axios acquisition has no bootstrap on explicit refresh and rejects conflicting response',async()=>{
 const {binding,send}=await fastClient();const dates=jest.fn();binding.subscribeDate(dates);
 let current=A;const network=jest.fn(async config=>({config,status:200,statusText:'OK',
   headers:{[lower]:current,[dateHeader]:JSON.stringify(nativeDate)},data:{status:200}}));
 const transport=axios.create({baseURL:'http://localhost',adapter:network});
 transport.interceptors.request.use(binding.request);transport.interceptors.response.use(binding.response);
 await transport.post('/api/mta/GetBTRDataCount');current=B;
 await expect(transport.post('/api/mta/GetBTRData')).rejects.toThrow('missing or stale');
 expect(send).toHaveBeenCalledTimes(1);expect(dates).toHaveBeenCalledTimes(1);
});


test('publication tokens must be strings rather than regex-coercible arrays',async()=>{
 const invalid=createMtaPublicationBinding(async()=>({data:{mode:'native',binding:[A],date_response:nativeDate,report_acquisition:true}}));
 await expect(invalid.request({url:'/api/mta/GetLastRunDate'})).rejects.toThrow('binding is unavailable');
 const {binding,reply}=await fastClient();const dates=jest.fn();binding.subscribeDate(dates);
 const config=await binding.request({url:'/api/mta/GetBTRData'});
 expect(()=>reply(config,A,nativeDate,{headers:{[lower]:[A],[dateHeader]:JSON.stringify(nativeDate)}})).toThrow('missing or stale');
 expect(dates).not.toHaveBeenCalled();
});
