import {render, fireEvent, screen, waitFor, cleanup} from '@testing-library/react';
import ParentDispatch from './Parent/Grid/ExpediteDispatches';
import ParentAvailability from './Parent/Grid/CreateAvailabilityAtParent';
import ChildGrid from './Child/Grid';
import ChildDispatch from './Child/Grid/ExpediteDispatches';
import ChildAvailability from './Child/Grid/CreateAvailabilityAtParent';
import {notifySuccess, notifyError} from '../../../../../../helpers/notify';

const mockSubmit=jest.fn();
const mockRefresh=jest.fn();
jest.mock('../../../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/Planning',()=>({
  useSubmitOpenExpediteRequest:()=>({mutateAsync:mockSubmit}),
}));
jest.mock('../../../../../../helpers/notify',()=>({notifyError:jest.fn(),notifySuccess:jest.fn(),notifyLoader:jest.fn()}));
jest.mock('../../../../../../helpers/utils',()=>({
  getColumnDefinationsMTA:()=>[],getProductAndLocationHeirarchiesFromEnv:()=>({}),
  createIconColumn:()=>({}),MainMenuItemsCustomization:()=>[],
}));
jest.mock('../../../../../../context/GridStateContext',()=>({
  GridStateContext:require('react').createContext({gridColDefs:null,setGlobalColDef:()=>{},refreshAfterRequest:()=>mockRefresh()}),
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
const variants=[['parent dispatch',ParentDispatch],['parent availability',ParentAvailability],
  ['child summary',ChildGrid],['child dispatch',ChildDispatch],['child availability',ChildAvailability]] as const;

test.each(variants)('%s submits the selected main row, not the first detail row',async(name,Component)=>{
  mockSubmit.mockResolvedValue({status:200});
  const rows=[{sc:'wrong-first',wc:'wrong-location',parentWhCode:'wrong-parent'},
    {sc:'338',wc:'DP010290',parentWhCode:'Parent-2',pl:'Parent display name',eta:'2026-10-21',intransit:[]}];
  render(<Component data={{data:rows,uiConfig:[],stockData:[{skucode:'wrong-first',whcode:'wrong-location',pl:'wrong-display'}],transitData:[]}}
    paginationProps={{} as any} onOpenDailyDataGraph={()=>{}} currentCategory="expedite" currentTab="normal"/>);
  fireEvent.click(screen.getByText('Select second row'));
  fireEvent.click(screen.getByText('Request expediting'));
  fireEvent.click(screen.getByText('Submit request'));
  await waitFor(()=>expect(mockSubmit).toHaveBeenCalledWith({skuCode:'338',whCode:'DP010290',parentWhCode:'Parent-2',
    request:'Please expedite',eta:'2026/10/21'}));
  await waitFor(()=>expect(notifySuccess).toHaveBeenCalled());
  expect(mockRefresh).toHaveBeenCalledTimes(1);
});

test('a rejected write produces an error and no success notification',async()=>{
  mockSubmit.mockRejectedValue(new Error('Scope denied'));
  const rows=[{}, {sc:'338',wc:'DP010290',parentWhCode:'Parent-2',eta:null,intransit:[]}];
  render(<ChildDispatch data={{data:rows}} paginationProps={{} as any} onOpenDailyDataGraph={()=>{}}
    currentCategory="expedite" currentTab="normal"/>);
  fireEvent.click(screen.getByText('Select second row'));
  fireEvent.click(screen.getByText('Request expediting'));
  fireEvent.click(screen.getByText('Submit request'));
  await waitFor(()=>expect(notifyError).toHaveBeenCalled());
  expect(notifySuccess).not.toHaveBeenCalled();
  expect(mockRefresh).not.toHaveBeenCalled();
});
