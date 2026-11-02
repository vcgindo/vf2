import axios from 'axios';
jest.mock('axios',()=>({__esModule:true,default:jest.fn()}));
import {act,renderHook} from '@testing-library/react';
import useGetLastRunData from './useGetLastRunData';
import {mtaPublicationBinding,refreshMtaReportBinding} from '../config/mta-publication-binding';
const mockRead=jest.fn(),mockDispatch=jest.fn();
jest.mock('../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR',()=>({useGetLastRunDate:()=>({mutateAsync:mockRead})}));
jest.mock('react-redux',()=>({useDispatch:()=>mockDispatch}));
const date=(formatted:string,rawDate=formatted)=>({data:{data:[{formatted,rawDate}]}});
const deferred=()=>{let resolve!:(value:any)=>void,reject!:(error:any)=>void;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return{promise,resolve,reject};};
beforeEach(()=>{jest.clearAllMocks();mtaPublicationBinding.refresh(false);mockRead.mockResolvedValue(date('03 Nov 2026','2026-11-03'));});

test.each(['success','error'])('refresh updates the companion date and ignores an old %s',async oldOutcome=>{
 const {result}=renderHook(()=>useGetLastRunData());await act(async()=>{});
 expect(result.current.date).toBe('03 Nov 2026');
 const old=deferred(),recent=deferred();
 mockRead.mockReturnValueOnce(old.promise).mockReturnValueOnce(recent.promise);
 act(()=>refreshMtaReportBinding());
 expect(result.current.date).toBe('Loading');
 act(()=>refreshMtaReportBinding());
 await act(async()=>{recent.resolve(date('04 Nov 2026','2026-11-04'));});
 await act(async()=>{if(oldOutcome==='success')old.resolve(date('obsolete'));else old.reject(new Error('obsolete'));});
 expect(result.current.date).toBe('04 Nov 2026');
 expect(mockDispatch.mock.calls.map(call=>call[0].payload)).toEqual(['2026-11-03','2026-11-04']);
});

test('providedDate bypasses both initial reads and refresh notifications',async()=>{
 const {result}=renderHook(()=>useGetLastRunData('Provided publication date'));
 await act(async()=>{refreshMtaReportBinding();});
 expect(result.current.date).toBe('Provided publication date');
 expect(mockRead).not.toHaveBeenCalled();
 expect(mockDispatch).not.toHaveBeenCalled();
});

test('unmount removes the subscription and discards a late date',async()=>{
 const pending=deferred();mockRead.mockReturnValueOnce(pending.promise);
 const {unmount}=renderHook(()=>useGetLastRunData());unmount();
 await act(async()=>{refreshMtaReportBinding();pending.resolve(date('obsolete'));});
 expect(mockRead).toHaveBeenCalledTimes(1);
 expect(mockDispatch).not.toHaveBeenCalled();
});

test('current error is unavailable and explicit refresh retries the date',async()=>{
 const log=jest.spyOn(console,'error').mockImplementation(()=>{});
 mockRead.mockRejectedValueOnce(new Error('unavailable'));
 const {result}=renderHook(()=>useGetLastRunData());await act(async()=>{});
 expect(result.current.date).toBe('Date Unavailable');
 await act(async()=>{refreshMtaReportBinding();});
 expect(result.current.date).toBe('03 Nov 2026');
 log.mockRestore();
});

const enableAcquisition = async () => {
 (axios as unknown as jest.Mock).mockResolvedValue({data:{mode:'native',binding:'a'.repeat(64),report_acquisition:true,
   date_response:{status:200,data:[{formatted:'03 Nov 2026',rawDate:'2026-11-03'}]}}});
 await mtaPublicationBinding.request({url:'/api/mta/GetLastRunDate'});
};
const acceptReport = async () => {
 const config=await mtaPublicationBinding.request({url:'/api/mta/GetBTRData'});
 return mtaPublicationBinding.response({config,status:200,headers:{'x-vectorflow-publication':'b'.repeat(64),
   'x-vectorflow-publication-date':JSON.stringify({status:200,data:[{formatted:'04 Nov 2026',rawDate:'2026-11-04'}]})},data:{status:200}});
};

test('fast report refresh skips date HTTP and failed reports leave date unavailable',async()=>{
 await enableAcquisition();const {result}=renderHook(()=>useGetLastRunData());await act(async()=>{});
 expect(result.current.date).toBe('03 Nov 2026');
 act(()=>refreshMtaReportBinding());
 expect(result.current.date).toBe('Date Unavailable');expect(mockRead).toHaveBeenCalledTimes(1);
 expect(mockDispatch.mock.calls[mockDispatch.mock.calls.length-1]?.[0].payload).toBe('');
 const failed=await mtaPublicationBinding.request({url:'/api/mta/GetBTRDataCount'});
 expect(()=>mtaPublicationBinding.response({config:failed,status:200,data:{status:400},headers:{}})).toThrow();
 expect(result.current.date).toBe('Date Unavailable');
 await act(async()=>{await acceptReport();});
 expect(result.current.date).toBe('04 Nov 2026');expect(mockRead).toHaveBeenCalledTimes(1);
 expect(mockDispatch.mock.calls[mockDispatch.mock.calls.length-1]?.[0].payload).toBe('2026-11-04');
});

test('fast refresh ignores pending old date and superseded report metadata',async()=>{
 await enableAcquisition();const old=deferred();mockRead.mockReturnValueOnce(old.promise);
 const {result}=renderHook(()=>useGetLastRunData());
 act(()=>refreshMtaReportBinding());
 const config=await mtaPublicationBinding.request({url:'/api/mta/GetBTRData'});
 act(()=>refreshMtaReportBinding());
 await act(async()=>{old.resolve(date('obsolete'));});
 expect(()=>mtaPublicationBinding.response({config,status:200,headers:{}})).toThrow('superseded');
 expect(result.current.date).toBe('Date Unavailable');
 await act(async()=>{await acceptReport();});expect(result.current.date).toBe('04 Nov 2026');
});

test('fast date subscription respects provided date and unmount',async()=>{
 await enableAcquisition();const provided=renderHook(()=>useGetLastRunData('Provided'));
 const mounted=renderHook(()=>useGetLastRunData());await act(async()=>{});mounted.unmount();mockDispatch.mockClear();
 await act(async()=>{refreshMtaReportBinding();await acceptReport();});
 expect(provided.result.current.date).toBe('Provided');expect(mockDispatch).not.toHaveBeenCalled();
});
