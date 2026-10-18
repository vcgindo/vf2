// Approved narrow Planning identifier exception; MTO is unchanged.
import {render, fireEvent, screen, waitFor, cleanup, act} from '@testing-library/react';
import Planning from '..';
import {notifyError} from '../../../../../../helpers/notify';
const mockPlanningState:any={};
jest.mock('../usePlanning',()=>({__esModule:true,default:()=>mockPlanningState}));
jest.mock('../ChartView',()=>()=>null);
jest.mock('../ActionToolBar',()=>()=>null);
jest.mock('../GridView',()=>({__esModule:true,default:(props:any)=>{
  const Component=require('./Parent/Grid/ExpediteDispatches').default;
  return require('react').createElement(Component,{data:props.currentGridData.expediteDispatches,
    paginationProps:{},currentCategory:'ExpediteFromParent',currentTab:'expediteDispatches',onOpenDailyDataGraph:()=>{}});
}}));
jest.mock('../../../../../../components/VectorFLOW/layouts/SelectCategory',()=>()=>null);
jest.mock('../../../../../../components/VectorFLOW/commons/VFOverlay',()=>()=>null);
jest.mock('../../../../../../components/VectorFLOW/commons/DailyDataGraphModal',()=>()=>null);
jest.mock('../../../../../../components/VectorFLOW/commons/NormChangeHistoryTable',()=>()=>null);
jest.mock('../../../../../../components/VectorFLOW/commons/VFTable',()=>()=>null);
jest.mock('../../../../../../components/VectorFLOW/commons/VFLoader',()=>()=>null);
jest.mock('../../../../MTO/Common/Loader',()=>()=>null);
jest.mock('../../../../../../components/commons/lastRundate',()=>()=>null);
const mockSubmit=jest.fn();
jest.mock('../../../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/Planning',()=>({
  useSubmitOpenExpediteRequest:()=>({mutateAsync:mockSubmit}),
}));
jest.mock('../../../../../../helpers/notify',()=>({notifyError:jest.fn(),notifySuccess:jest.fn(),notifyLoader:jest.fn()}));
jest.mock('../../../../../../helpers/utils',()=>({
  getColumnDefinationsMTA:()=>[],getProductAndLocationHeirarchiesFromEnv:()=>({}),
  createIconColumn:()=>({}),MainMenuItemsCustomization:()=>[],
}));
jest.mock('../../../../../../context/GridStateContext',()=>({
  GridStateContext:require('react').createContext({gridColDefs:null,setGlobalColDef:()=>{}}),
}));
jest.mock('../../BPR/BPRCellRenderers',()=>({BPRTagsCellRenderer:()=>null}));
jest.mock('../../BPR/BPRGraphCellRenderer',()=>()=>null);
jest.mock('../../../InsightsAndTrends/BTR/ColorCellRenderer',()=>()=>null);
jest.mock('../GridView/GridViewTable',()=>({__esModule:true,default:(props:any)=>{
  const React=require('react');
  return React.createElement('div',{},
    React.createElement('button',{onClick:()=>props.agGridProps.onRowClicked({data:props.agGridRowData[1]})},'Select second row'),
    React.createElement('button',{onClick:props.onRequestExpediting},'Request expediting'));
}}));
jest.mock('../../BPR/RequestExpeditingModal',()=>({__esModule:true,default:(props:any)=>
  props.isOpen?require('react').createElement('button',{onClick:()=>props.onSubmit('Please expedite')},'Submit request'):null,
}));


afterEach(()=>{cleanup();jest.clearAllMocks();});
test.each(['337','00337','9007199254740993','1e3'])('actual Planning parent preserves identifier %s through selected-row request',async(sku)=>{
  mockSubmit.mockResolvedValue({status:200});
  const row={sc:sku,wc:'001',parentWhCode:'0002',n:'36',rtq:'25',pin:'69.44',eta:null,remark:null};
  const grid={data:[{...row,sc:'wrong-first'},row],stockData:[],transitData:[],uiConfig:[]};
  Object.assign(mockPlanningState,{currentGridData:{expediteDispatches:grid},currentView:'grid',
    currentCategory:'ExpediteFromParent',currentTab:'expediteDispatches',isSelectCategoryOpen:false,
    isDataLoading:false,getFloatingTabsList:()=>[],setGlobalColDef:()=>{},gridColDefs:null});
  render(<Planning/>);
  // Parent useEffect must have executed before a human can select and submit.
  await waitFor(()=>expect(row.n).toBe(36));
  expect(row).toEqual({sc:sku,wc:'001',parentWhCode:'0002',n:36,rtq:25,pin:69.44,eta:null,remark:null});
  fireEvent.click(screen.getByText('Select second row'));
  fireEvent.click(screen.getByText('Request expediting'));
  await act(async()=>{fireEvent.click(screen.getByText('Submit request'));});
  await waitFor(()=>expect(mockSubmit).toHaveBeenCalledTimes(1));
  expect(mockSubmit).toHaveBeenCalledWith({skuCode:sku,whCode:'001',parentWhCode:'0002',request:'Please expedite',eta:null});
  expect(notifyError).not.toHaveBeenCalled();
});
