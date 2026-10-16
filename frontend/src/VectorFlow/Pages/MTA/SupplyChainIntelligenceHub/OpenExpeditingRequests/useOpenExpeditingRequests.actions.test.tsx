import {act, renderHook, waitFor} from '@testing-library/react';
import useOpenExpeditingRequests from './useOpenExpeditingRequests';
import {notifyError, notifySuccess} from '../../../../../helpers/notify';

const mockData=jest.fn(), mockAdd=jest.fn(), mockHistory=jest.fn();
const mockConfig=jest.fn(), mockState=jest.fn();
let mockHeaders:any;

jest.mock('../../../../Services/MTA/SupplyChainIntelligenceHub/OpenExpeditingRequests',()=>({
  useGetOpenExpediteRequestData:()=>({mutateAsync:mockData,isLoading:false}),
  useAddRemarkForExpedite:()=>({mutateAsync:mockAdd}),
  useGetRemarkDetailsForExpedite:()=>({mutateAsync:mockHistory}),
}));
jest.mock('../../../../Services/MTA/Common/UserUIConfig',()=>({
  useGetState:()=>({mutateAsync:mockState}),
}));
jest.mock('../../../../Services/MTA/Common/UIConfig',()=>({
  useGetUIConfigData:()=>({mutateAsync:mockConfig,isLoading:false}),
}));
jest.mock('../../../../../context',()=>({
  useUserData:()=>({user:{user:{theme_ui:'NOIRFUSION'}}}),
}));
jest.mock('../../../../../hooks/useBPRFilter',()=>()=>({
  state:{availabilityFilter:{filters:[]}},setState:jest.fn(),onDelete:jest.fn(),
}));
jest.mock('../../../../../hooks/useGetLastRunData',()=>()=>({date:'2026-10-18'}));
jest.mock('../../../../../hooks/useViewPort',()=>()=>({
  getGridZoom:()=>1,getScreenZoomValue:()=>1,
}));
jest.mock('../../../../../helpers/utils',()=>({
  getColumnDefinationsMTA:(_source:any,headers:any)=>{mockHeaders=headers;return [];},
  MainMenuItemsCustomization:jest.fn(),
}));
jest.mock('../../../../../helpers/notify',()=>({
  notifyLoader:jest.fn(()=>1),notifyError:jest.fn(),notifySuccess:jest.fn(),
}));
jest.mock('react-toastify',()=>({toast:{dismiss:jest.fn()}}));
jest.mock('./ColorCellRenderer',()=>()=>null);
jest.mock('./ETACellRenderer',()=>()=>null);
jest.mock('./ShowRemarkCellRenderer',()=>()=>null);
jest.mock('./SubmitRemarkCellRenderer',()=>()=>null);

const response=(rows:any[]=[])=>({data:{data:{data:rows}}});
const target=()=>{const cell=document.createElement('div');cell.setAttribute('role','gridcell');return cell;};
const row=(id:number, overrides:any={})=>({id,sc:`SKU-${id}`,wc:`WH-${id}`,eta:null,action:'',...overrides});

beforeEach(()=>{
  jest.clearAllMocks();mockHeaders=undefined;
  mockData.mockResolvedValue(response());
  mockConfig.mockResolvedValue({data:{data:[]}});
  mockState.mockResolvedValue({data:{data:''}});
});

test('single remark callback submits the actual clicked expedite row with null ETA',async()=>{
  mockAdd.mockResolvedValue({status:200});
  const {result}=renderHook(useOpenExpeditingRequests);
  await waitFor(()=>expect(mockHeaders?.action?.onCellClicked).toBeDefined());
  act(()=>mockHeaders.action.onCellClicked({event:{target:target()},
    data:row(2,{sc:'ACTUAL-SKU',wc:'ACTUAL-WH',eta:null})}));
  act(()=>result.current.updateRemark({currentTarget:{value:'Contacted carrier'}}));
  await act(async()=>{await result.current.onSubmitRemark();});

  expect(mockAdd).toHaveBeenCalledWith({data:[{SKUCode:'ACTUAL-SKU',WHCode:'ACTUAL-WH',
    Remark:'Contacted carrier',ETA:null}]});
  expect(notifySuccess).toHaveBeenCalledWith('Remark Has Been submitted');
});

test('edited expedite rows are submitted together through the batch command model',async()=>{
  mockAdd.mockResolvedValue({status:200});
  const {result}=renderHook(useOpenExpeditingRequests);
  await waitFor(()=>expect(mockData).toHaveBeenCalled());
  act(()=>result.current.agGridProps.onCellValueChanged?.({data:row(1,{action:'First'})} as any));
  act(()=>result.current.agGridProps.onCellValueChanged?.({data:row(2,{
    action:'Second',eta:'2026-10-23'})} as any));
  await act(async()=>{await result.current.onSubmitEditedRows();});

  expect(mockAdd).toHaveBeenCalledWith({data:[
    {SKUCode:'SKU-1',WHCode:'WH-1',Remark:'First',ETA:null},
    {SKUCode:'SKU-2',WHCode:'WH-2',Remark:'Second',ETA:'2026/10/23'},
  ]});
});

test('a rejected expedite modal write reports failure without success',async()=>{
  mockAdd.mockRejectedValue(new Error('Scope denied'));
  const {result}=renderHook(useOpenExpeditingRequests);
  await waitFor(()=>expect(mockHeaders?.action?.onCellClicked).toBeDefined());
  await waitFor(()=>expect(notifySuccess).toHaveBeenCalledWith('Data Loaded Successfully'));
  (notifySuccess as jest.Mock).mockClear();
  act(()=>mockHeaders.action.onCellClicked({event:{target:target()},data:row(3)}));
  act(()=>result.current.updateRemark({currentTarget:{value:'Contacted carrier'}}));
  await act(async()=>{await result.current.onSubmitRemark();});
  expect(notifyError).toHaveBeenCalledWith('Scope denied');
  expect(notifySuccess).not.toHaveBeenCalled();
});
