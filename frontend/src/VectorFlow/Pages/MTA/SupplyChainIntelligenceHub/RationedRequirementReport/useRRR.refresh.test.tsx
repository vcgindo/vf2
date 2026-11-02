import {act,renderHook} from '@testing-library/react';
import useRRR from './useRRR';
import {mtaPublicationBinding} from '../../../../../config/mta-publication-binding';
const mockRows=jest.fn(),mockCount=jest.fn();
jest.mock('../../../../Services/MTA/SupplyChainIntelligenceHub/RRR',()=>({
 useGetRRRData:()=>({mutateAsync:mockRows}),useGetRRRDataCount:()=>({mutateAsync:mockCount}),
}));
jest.mock('../../../../Services/MTA/Common/UIConfig',()=>({useGetUIConfigData:()=>({mutateAsync:async()=>({data:{data:[]}})})}));
jest.mock('../../../../Services/MTA/Common/UserUIConfig',()=>({useGetState:()=>({mutateAsync:async()=>({data:{data:''}})})}));
jest.mock('../../../../../context',()=>({useUserData:()=>({isSideBarOpen:true})}));
jest.mock('react-redux',()=>({useSelector:(select:any)=>select({mta:{EnvConfig:{RRR_ROWS_PER_PAGE:'50'}}})}));
jest.mock('../../../../../hooks/useBPRFilter',()=>()=>({state:{},setState:jest.fn(),onDelete:jest.fn()}));
jest.mock('../../../../../hooks/useGetLastRunData',()=>()=>({date:'2026-11-03'}));
jest.mock('../../../../../helpers/utils',()=>({getColumnDefinationsMTA:()=>[],convertUiConfigToOptions:()=>[]}));
jest.mock('../../../../../helpers/notify',()=>({notifyError:jest.fn(),notifyLoader:jest.fn(),notifySuccess:jest.fn()}));
jest.mock('react-toastify',()=>({toast:{dismiss:jest.fn()}}));
jest.mock('./RRRCellRenderers',()=>({}));
beforeEach(()=>{jest.clearAllMocks();mockRows.mockResolvedValue({data:{data:[{SKUCode:'new'}]}});mockCount.mockResolvedValue({data:{recordCount:2}});});

test('explicit filter retry starts a fresh binding after a stale-publication error',async()=>{
 const refresh=jest.spyOn(mtaPublicationBinding,'refresh');
 mockCount.mockRejectedValueOnce(new Error('publication changed'));
 const {result}=renderHook(useRRR);
 await act(async()=>{await result.current.onApplyFilter({});});
 expect(result.current.RRRRowData).toEqual([]);
 await act(async()=>{await result.current.onApplyFilter({});});
 expect(refresh).toHaveBeenCalledTimes(2);
 expect(result.current.RRRRowData).toEqual([{SKUCode:'new'}]);
 expect(result.current.RRRDataCount).toBe(2);
 refresh.mockRestore();
});

test('a superseded pair cannot replace or clear newer filter results',async()=>{
 let fail!:(reason:any)=>void,finish!:(value:any)=>void;
 mockRows.mockReturnValueOnce(new Promise((_resolve,reject)=>{fail=reject;}));
 mockCount.mockReturnValueOnce(new Promise(resolve=>{finish=resolve;}));
 const {result}=renderHook(useRRR);let obsolete!:Promise<void>;
 act(()=>{obsolete=result.current.onApplyFilter({old:true});});
 await act(async()=>{await result.current.onApplyFilter({new:true});});
 await act(async()=>{fail(new Error('obsolete failure'));finish({data:{recordCount:99}});await obsolete;});
 expect(result.current.RRRRowData).toEqual([{SKUCode:'new'}]);
 expect(result.current.RRRDataCount).toBe(2);
 expect(result.current.reportError).toBeNull();
});
