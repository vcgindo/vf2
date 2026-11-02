import {act,renderHook} from '@testing-library/react';
import {useBOR} from '../BuyerOrderReport/useBOR';
import {useBORColorBandwise} from '../BuyerOrderReport Color Bandwise/useBORColorBandwise';
const mockRows=jest.fn(),mockCount=jest.fn(),mockSubmit=jest.fn(),mockConfig=jest.fn(),mockState=jest.fn(),mockDispatch=jest.fn();
jest.mock('../../../../Services/MTA/SupplyChainIntelligenceHub/BuyerOrderReport',()=>({
 useBORData:()=>({mutateAsync:mockRows}),useBORDataCount:()=>({mutateAsync:mockCount}),
 useSubmitBORRemark:()=>({mutateAsync:mockSubmit}),useGetBORRemarkHistory:()=>({mutateAsync:jest.fn()}),
}));
jest.mock('../../../../Services/MTA/SupplyChainIntelligenceHub/BORColorBandWise',()=>({
 useGetBORColorBandWisData:()=>({mutateAsync:mockRows}),useGetBORColorBandWiseRecordCount:()=>({mutateAsync:mockCount}),
 useSubmitBOROARemark:()=>({mutateAsync:mockSubmit}),useGetBOROARemarkHistory:()=>({mutateAsync:jest.fn()}),
}));
jest.mock('../../../../Services/MTA/SupplyChainIntelligenceHub/BPR',()=>({useGetDailyData:()=>({mutateAsync:jest.fn()})}));
jest.mock('../../../../Services/MTA/Common/UIConfig',()=>({useGetUIConfigData:()=>({mutateAsync:mockConfig,isLoading:false})}));
jest.mock('../../../../Services/MTA/Common/UserUIConfig',()=>({useGetState:()=>({mutateAsync:mockState})}));
jest.mock('react-redux',()=>({useDispatch:()=>mockDispatch,useSelector:(select:any)=>select({mta:{EnvConfig:{},dailyData:{}}})}));
jest.mock('../../../../../hooks/useBPRFilter',()=>()=>({state:{},setState:jest.fn(),onDelete:jest.fn()}));
jest.mock('../../../../../hooks/useGetLastRunData',()=>()=>({date:'2026-11-03'}));
jest.mock('../../../../../hooks/useViewPort',()=>()=>({getGridZoom:()=>1,getScreenZoomValue:()=>1}));
jest.mock('../../../../../helpers/utils',()=>({getColumnDefinationsMTA:()=>[],convertUiConfigToOptions:()=>[]}));
jest.mock('../../../../../helpers/notify',()=>({notifyError:jest.fn(),notifyLoader:jest.fn(),notifySuccess:jest.fn()}));
jest.mock('react-toastify',()=>({toast:{dismiss:jest.fn()}}));
jest.mock('./BPRGraphCellRenderer',()=>()=>null);
jest.mock('./BPRCellRenderers',()=>({}));
jest.mock('../BuyerOrderReport/BORCellRenderers',()=>({}));
jest.mock('../BuyerOrderReport/CellRenderer',()=>({}));
beforeEach(()=>{
 jest.clearAllMocks();mockRows.mockResolvedValue({data:{data:[{SKUCode:'old'}]}});
 mockCount.mockResolvedValue({data:{recordCount:1,data:[{count:1}]}});
 mockSubmit.mockResolvedValue({status:200,data:{msg:'Saved'}});
 mockConfig.mockResolvedValue({data:{data:[]}});mockState.mockResolvedValue({data:{data:''}});
});
test.each([['BOR',useBOR],['BOROA',useBORColorBandwise]] as const)('%s remarks rebuild the related pair without repeating the mutation',async(name,hook)=>{
 const {result}=renderHook(hook as any);const current=()=>result.current as any;
 await act(async()=>{await current().onApplyFilter({});});
 act(()=>current().agGridProps.onCellValueChanged({data:{SKUCode:'sku',WHCode:'loc',WhCode:'loc',SupplierCode:'supplier',remarks:'Saved'}}));
 mockRows.mockResolvedValueOnce({data:{data:[{SKUCode:'new',Remark:'Saved'}]}});
 await act(async()=>{await current().onSubmitRemarks();});
 expect(mockSubmit).toHaveBeenCalledTimes(1);
 expect(mockRows).toHaveBeenCalledTimes(2);
 expect(mockCount).toHaveBeenCalledTimes(2);
 expect(current().rowData).toEqual([{SKUCode:'new',Remark:'Saved'}]);
});
