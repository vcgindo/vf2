import { act, renderHook } from '@testing-library/react';
import useDBM from './useDBM';

const mockRows=jest.fn(), mockCount=jest.fn(), mockApply=jest.fn(), mockSleep=jest.fn();
const mockConfig=jest.fn(), mockState=jest.fn(), mockDispatch=jest.fn();
jest.mock('../../../../Services/MTA/DBM',()=>({
  useGetDBMData:()=>({mutateAsync:mockRows,isLoading:false}),
  useGetDBMDataCount:()=>({mutateAsync:mockCount,isLoading:false}),
  useGetDBMApplySelectedNorm:()=>({mutateAsync:mockApply}),
  useGetDBMUpdateSleepTbl:()=>({mutateAsync:mockSleep}),
}));
jest.mock('../../../../Services/MTA/Common/UIConfig',()=>({useGetUIConfigData:()=>({mutateAsync:mockConfig,isLoading:false})}));
jest.mock('../../../../Services/MTA/Common/UserUIConfig',()=>({useGetState:()=>({mutateAsync:mockState})}));
jest.mock('../../../../Services/MTA/SupplyChainIntelligenceHub/BPR',()=>({useGetDailyData:()=>({mutateAsync:jest.fn()})}));
jest.mock('react-redux',()=>({useDispatch:()=>mockDispatch,useSelector:(select:any)=>select({mta:{EnvConfig:{DBM_ROWS_PER_PAGE:'50'},dailyData:{}}})}));
jest.mock('../../../../../hooks/useBPRFilter',()=>()=>({state:{kept:true},setState:jest.fn(),onDelete:jest.fn()}));
jest.mock('../../../../../hooks/useGetLastRunData',()=>()=>({date:'2026-10-19'}));
jest.mock('../../../../../helpers/utils',()=>({getColumnDefinationsMTA:()=>[],convertUiConfigToOptions:()=>[]}));
jest.mock('../../../../../helpers/notify',()=>({notifyError:jest.fn(),notifyLoader:jest.fn(),notifySuccess:jest.fn()}));
jest.mock('react-toastify',()=>({toast:{dismiss:jest.fn()}}));
jest.mock('../../SupplyChainIntelligenceHub/BPR/BPRGraphCellRenderer',()=>()=>null);
jest.mock('./dbmTick',()=>({DBMTickCellRenderer:()=>null}));
jest.mock('./SuggestionCategoryCellRendere',()=>()=>null);

beforeEach(()=>{
  jest.clearAllMocks();
  mockRows.mockResolvedValue({status:200,data:{data:[{SKUCode:'before'}]}});
  mockCount.mockResolvedValue({status:200,data:{recordCount:1}});
  mockConfig.mockResolvedValue({data:{data:[]}});
  mockState.mockResolvedValue({data:{data:''}});
  mockApply.mockResolvedValue({status:200});
  mockSleep.mockResolvedValue({status:200});
});

test.each(['Apply','Sleep'])('%s commits one new count/grid pair and never replays the mutation',async action=>{
  const {result}=renderHook(useDBM);
  await act(async()=>{});
  (result.current.gridRef as any).current={api:{getSelectedRows:()=>[{SKUCode:'sku',LocCode:'loc'}]}};
  mockRows.mockResolvedValueOnce({status:200,data:{data:[{SKUCode:'after'}]}});
  mockCount.mockResolvedValueOnce({status:200,data:{recordCount:2}});
  await act(async()=>{await (action==='Apply'?result.current.handleGoButton(1):result.current.handleGoButtonForSleep(1));});
  expect(action==='Apply'?mockApply:mockSleep).toHaveBeenCalledTimes(1);
  expect(mockRows).toHaveBeenCalledTimes(2);
  expect(mockCount).toHaveBeenCalledTimes(2);
  expect(result.current.DBMRowData).toEqual([{SKUCode:'after'}]);
  expect(result.current.DBMDataCount).toBe(2);
  expect(mockRows.mock.calls[1][0]).toMatchObject({filters:{kept:true},paginationParameter:{pageNumber:1,recordsPerPage:50}});
});

test('a failed post-action refresh can retry reads without repeating Apply',async()=>{
  const {result}=renderHook(useDBM);
  await act(async()=>{});
  (result.current.gridRef as any).current={api:{getSelectedRows:()=>[{SKUCode:'sku',LocCode:'loc'}]}};
  mockCount.mockRejectedValueOnce(new Error('publication changed'));
  await act(async()=>{await result.current.handleGoButton(1);});
  expect(result.current.DBMRowData).toEqual([]);
  expect(result.current.DBMDataCount).toBeUndefined();
  await act(async()=>{await result.current.handleApplyFilter({kept:true});});
  expect(result.current.DBMRowData).toEqual([{SKUCode:'before'}]);
  expect(mockApply).toHaveBeenCalledTimes(1);
});
