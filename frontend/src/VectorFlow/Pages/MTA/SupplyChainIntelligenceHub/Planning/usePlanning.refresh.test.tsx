import {act,renderHook} from '@testing-library/react';
import usePlanning from './usePlanning';
const mockSummary=jest.fn(),mockGraph=jest.fn(),mockGrid=jest.fn(),mockCount=jest.fn(),mockDispatch=jest.fn();
jest.mock('../../../../Services/MTA/SupplyChainIntelligenceHub/Planning',()=>({
 useGetPlanningDataCount:()=>({mutateAsync:mockSummary}),useGetPlanningDataGraph:()=>({mutateAsync:mockGraph}),
 useGetPlanningDataGrid:()=>({mutateAsync:mockGrid}),useGetPlanningDataGridCount:()=>({mutateAsync:mockCount}),
}));
jest.mock('../../../../Services/MTA/SupplyChainIntelligenceHub/BPR',()=>({useGetDailyData:()=>({mutateAsync:jest.fn()})}));
jest.mock('../../../../Services/MTA/Common/UIConfig',()=>({useGetUIConfigData:()=>({mutateAsync:async()=>({data:{data:[]}})})}));
jest.mock('react-redux',()=>({useDispatch:()=>mockDispatch,useSelector:(select:any)=>select({mta:{EnvConfig:{PLANNING_ROWS_PER_PAGE:'50'},dailyData:{}}})}));
jest.mock('../../../../../hooks/useBPRFilter',()=>()=>({state:{kept:true},setState:jest.fn(),onDelete:jest.fn()}));
jest.mock('../../../../../performance/screenProbe',()=>({useScreenProbe:jest.fn(),beginScreen:jest.fn(),screenRendered:jest.fn()}));
jest.mock('../../../../../helpers/notify',()=>({notifyError:jest.fn(),notifyLoader:jest.fn(),notifySuccess:jest.fn()}));
jest.mock('react-toastify',()=>({toast:{dismiss:jest.fn()}}));
const grid=(name:string)=>({data:{data:{data:{createAvailabilityAtParent:[{name}],expediteDispatches:[{name}]},uiConfig:[]}}});
const graph=(name:string)=>({data:{data:{data:{name}}}});
beforeEach(()=>{
 jest.clearAllMocks();
 mockSummary.mockResolvedValue({data:{businessDate:'2026-11-03',data:[]}});
 mockGraph.mockResolvedValue(graph('old'));
 mockGrid.mockResolvedValue(grid('old'));
 mockCount.mockResolvedValue({data:{data:{createAvailabilityAtParent:1,expediteDispatches:1}}});
});
const open=async(result:any)=>{
 await act(async()=>{await result.current.handlePlanningQuadrantClick('ExpediteToChild');});
 await act(async()=>{await result.current.onViewChange('grid');});
};

test('post-request parent refresh preserves page/filter and commits new count/grid/chart while a late old grid is ignored',async()=>{
 const {result}=renderHook(usePlanning);await act(async()=>{});await open(result);
 let finish!:(value:any)=>void;
 mockGrid.mockReturnValueOnce(new Promise(resolve=>{finish=resolve;}));
 await act(async()=>{result.current.paginationProps.handleChangePage(3);});
 mockGraph.mockResolvedValueOnce(graph('new'));
 mockGrid.mockResolvedValueOnce(grid('new'));
 mockCount.mockResolvedValueOnce({data:{data:{createAvailabilityAtParent:2,expediteDispatches:2}}});
 await act(async()=>{await result.current.refreshAfterRequest();});
 expect(result.current.paginationProps.currentPage).toBe(3);
 expect(result.current.planningCounts.childExpediteCount).toBe(2);
 expect(result.current.currentGraphData).toEqual({name:'new'});
 expect(result.current.currentGridData.expediteDispatches.data).toEqual([{name:'new'}]);
 expect(mockGrid.mock.calls[mockGrid.mock.calls.length-1][0]).toMatchObject({filters:{kept:true},paginationParameter:{pageNumber:3,recordsPerPage:50}});
 await act(async()=>{finish(grid('late old'));});
 expect(result.current.currentGridData.expediteDispatches.data).toEqual([{name:'new'}]);
});

test('failed refresh hides old descendants and existing filter retry rebuilds the set without a mutation',async()=>{
 const {result}=renderHook(usePlanning);await act(async()=>{});await open(result);
 mockGraph.mockRejectedValueOnce(new Error('publication changed'));
 await act(async()=>{await result.current.refreshAfterRequest();});
 expect(result.current.fulfillmentError).toBeTruthy();
 expect(result.current.currentGridData).toBeUndefined();
 expect(result.current.currentGraphData).toBeUndefined();
 await act(async()=>{await result.current.onApplyFilter({kept:true});});
 expect(result.current.fulfillmentError).toBeNull();
 expect(result.current.currentGridData.expediteDispatches.data).toEqual([{name:'old'}]);
 expect(result.current.currentGraphData).toEqual({name:'old'});
});

test('late submission on the chooser replaces the summary request and releases its overlay',async()=>{
 const {result}=renderHook(usePlanning);await act(async()=>{});await open(result);
 const late=result.current.refreshAfterRequest;
 let finish!:(value:any)=>void;
 mockSummary.mockReturnValueOnce(new Promise(resolve=>{finish=resolve;}));
 await act(async()=>{result.current.onGoBack();});
 const graphCalls=mockGraph.mock.calls.length,gridCalls=mockGrid.mock.calls.length;
 expect(result.current.isOverlayVisible).toBe(true);
 await act(async()=>{await late();});
 expect(result.current.isSelectCategoryOpen).toBe(true);
 expect(result.current.isOverlayVisible).toBe(false);
 expect(mockGraph).toHaveBeenCalledTimes(graphCalls);
 expect(mockGrid).toHaveBeenCalledTimes(gridCalls);
 await act(async()=>{finish({data:{businessDate:'2000-01-01',data:[]}});});
 expect(result.current.lastRunDate).not.toContain('2000');
});

test('late submission refreshes the current non-expedite category instead of an expedite child chart',async()=>{
 const {result}=renderHook(usePlanning);await act(async()=>{});await open(result);
 const late=result.current.refreshAfterRequest;
 await act(async()=>{result.current.onGoBack();});
 await act(async()=>{await result.current.handlePlanningQuadrantClick('ExcessInventory');});
 mockGraph.mockResolvedValueOnce(graph('current excess'));
 mockCount.mockResolvedValueOnce({data:{data:2}});
 mockGrid.mockResolvedValueOnce({data:{data:{name:'excess grid'}}});
 await act(async()=>{await late();});
 expect(mockGraph.mock.calls[mockGraph.mock.calls.length-1][0]).toMatchObject({category:'excessInventory',type:'review',filters:{kept:true}});
 expect(result.current.currentCategory).toBe('ExcessInventory');
 expect(result.current.currentGraphData).toEqual({name:'current excess'});
 expect(result.current.currentGridData).toEqual({name:'excess grid'});
});

test('late submission after Planning unmount does not start refresh reads',async()=>{
 const {result,unmount}=renderHook(usePlanning);await act(async()=>{});await open(result);
 const late=result.current.refreshAfterRequest;
 const before=[mockSummary.mock.calls.length,mockGraph.mock.calls.length,mockGrid.mock.calls.length,mockCount.mock.calls.length];
 unmount();await late();
 expect([mockSummary.mock.calls.length,mockGraph.mock.calls.length,mockGrid.mock.calls.length,mockCount.mock.calls.length]).toEqual(before);
});
