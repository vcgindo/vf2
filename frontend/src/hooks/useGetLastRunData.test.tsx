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
