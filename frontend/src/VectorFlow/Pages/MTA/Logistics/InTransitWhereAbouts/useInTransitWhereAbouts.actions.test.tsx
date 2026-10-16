import {act, renderHook, waitFor} from '@testing-library/react';
import useInTransitWhereAbouts from './useInTransitWhereAbouts';
import {notifyError, notifySuccess} from '../../../../../helpers/notify';

const mockCount=jest.fn(), mockData=jest.fn(), mockHistory=jest.fn();
const mockSubmit=jest.fn(), mockContacts=jest.fn(), mockConfig=jest.fn(), mockState=jest.fn();
let mockTransitHeaders:any;

jest.mock('../../../../Services/MTA/Logistics/InTransitWhereAbouts',()=>({
  useGetInTransitWhereAboutsDataCount:()=>({mutateAsync:mockCount,isLoading:false}),
  useGetInTransitWhereAboutsData:()=>({mutateAsync:mockData,isLoading:false}),
  useGetRemarkDetailsForInTransit:()=>({mutateAsync:mockHistory}),
  useSubmitRemarksForInTransit:()=>({mutateAsync:mockSubmit}),
  useGetTransporterDetails:()=>({mutateAsync:mockContacts}),
}));
jest.mock('../../../../Services/MTA/Common/UserUIConfig',()=>({
  useGetState:()=>({mutateAsync:mockState,isLoading:false}),
}));
jest.mock('../../../../Services/MTA/Common/UIConfig',()=>({
  useGetUIConfigData:()=>({mutateAsync:mockConfig,isLoading:false,isError:false}),
}));
jest.mock('../../../../../context',()=>({
  useUserData:()=>({user:{user:{theme_ui:'NOIRFUSION'}}}),
}));
jest.mock('../../../../../hooks/useBPRFilter',()=>()=>({
  state:{availabilityFilter:{filters:[]}},setState:jest.fn(),onDelete:jest.fn(),
}));
jest.mock('../../../../../hooks/useGetLastRunData',()=>()=>({date:'2026-07-04'}));
jest.mock('react-redux',()=>({
  useSelector:(select:any)=>select({mta:{EnvConfig:{IN_TRANSIT_WHEREABOUTS_ROWS_PER_PAGE:'100'}}}),
}));
jest.mock('../../../../../helpers/utils',()=>({
  getColumnDefinationsMTA:(_source:any,headers:any)=>{mockTransitHeaders=headers;return [];},
  mapInTransitWhereAboutsRowData:(rows:any)=>rows,
}));
jest.mock('../../../../../helpers/notify',()=>({
  notifyLoader:jest.fn(()=>1),notifyError:jest.fn(),notifySuccess:jest.fn(),
}));
jest.mock('react-toastify',()=>({toast:{dismiss:jest.fn()}}));
jest.mock('./MasterDetail',()=>()=>null);
jest.mock('./CellRenderers',()=>({
  ColorGroupCellRenderer:()=>null,CurrentLocationCellRenderer:()=>null,ETACellRenderer:()=>null,
}));
jest.mock('../../SupplyChainIntelligenceHub/OpenExpeditingRequests/ShowRemarkCellRenderer',()=>()=>null);
jest.mock('../../SupplyChainIntelligenceHub/OpenExpeditingRequests/SubmitRemarkCellRenderer',()=>()=>null);

const target=()=>{const cell=document.createElement('div');cell.setAttribute('role','gridcell');return cell;};
const transitRow=(order:string, overrides:any={})=>({OrderNo:order,SKUCode:'337',
  ReceiverLoc:'RECEIVER-2',SenderLocation:'PARENT-1',CurrentLoc:'OLD-HUB',ETA:null,...overrides});

beforeEach(()=>{
  jest.clearAllMocks();mockTransitHeaders=undefined;
  mockCount.mockResolvedValue({data:{recordCount:'0'}});
  mockData.mockResolvedValue({data:{data:[]}});
  mockConfig.mockResolvedValue({data:{data:[]}});
  mockState.mockResolvedValue({data:{data:''}});
});

test('single current-location callback keeps the clicked receiver, parent and null ETA',async()=>{
  mockSubmit.mockResolvedValue({status:200});
  const {result}=renderHook(useInTransitWhereAbouts);
  await waitFor(()=>expect(mockTransitHeaders?.CurrentLoc?.cellRendererParams?.onClick).toBeDefined());

  act(()=>mockTransitHeaders.CurrentLoc.cellRendererParams.onClick(
    {currentTarget:target()},transitRow('ORDER-A')));
  act(()=>result.current.setCurrentLocationValue('NEW-HUB'));
  await act(async()=>{await result.current.onSubmitCurrentLocation();});

  expect(mockSubmit).toHaveBeenCalledWith({data:[{OrderNo:'ORDER-A',SKUCode:'337',
    WhCode:'RECEIVER-2',ParentWHCode:'PARENT-1',Remarks:null,
    CurrentLocation:'NEW-HUB',ETA:null}]});
  expect(notifySuccess).toHaveBeenCalledWith('Data Has Been Submitted');
});

test('edited transit rows are submitted together through the batch command model',async()=>{
  mockSubmit.mockResolvedValue({status:200});
  const {result}=renderHook(useInTransitWhereAbouts);
  await waitFor(()=>expect(mockData).toHaveBeenCalled());
  act(()=>result.current.agGridProps.onCellValueChanged?.({data:transitRow('ORDER-A',{action:'A'})} as any));
  act(()=>result.current.agGridProps.onCellValueChanged?.({data:transitRow('ORDER-B',{
    ReceiverLoc:'RECEIVER-3',SenderLocation:null,ETA:'2026-10-21',action:'B'})} as any));
  await act(async()=>{await result.current.onSubmitEditedRows();});

  expect(mockSubmit).toHaveBeenCalledWith({data:[
    {OrderNo:'ORDER-A',SKUCode:'337',WhCode:'RECEIVER-2',ParentWHCode:'PARENT-1',
      Remarks:'A',CurrentLocation:'OLD-HUB',ETA:null},
    {OrderNo:'ORDER-B',SKUCode:'337',WhCode:'RECEIVER-3',ParentWHCode:null,
      Remarks:'B',CurrentLocation:'OLD-HUB',ETA:'2026/10/21'},
  ]});
});

test('a rejected transit modal write reports failure without success',async()=>{
  mockSubmit.mockRejectedValue(new Error('Scope denied'));
  const {result}=renderHook(useInTransitWhereAbouts);
  await waitFor(()=>expect(mockTransitHeaders?.ETA?.onCellClicked).toBeDefined());
  (notifySuccess as jest.Mock).mockClear();
  act(()=>mockTransitHeaders.ETA.onCellClicked({event:{target:target()},
    data:transitRow('ORDER-A',{ETA:'2026-10-22'})}));
  await act(async()=>{await result.current.onSubmitETA();});
  expect(notifyError).toHaveBeenCalledWith('Scope denied');
  expect(notifySuccess).not.toHaveBeenCalled();
});
