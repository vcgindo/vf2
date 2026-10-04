import { render, screen, fireEvent } from '@testing-library/react';
import { AgCharts } from 'ag-charts-react';
import DailyDataGraphModal from '.';

const mockDateFetch=jest.fn();
jest.mock('../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR',()=>({useGetLastRunDate:()=>({mutateAsync:mockDateFetch})}));
jest.mock('react-redux',()=>({useDispatch:()=>jest.fn()}));
jest.mock('../../../../context',()=>({useUserData:()=>({user:{user:{theme_ui:'NOIRFUSION'}}})}));
jest.mock('../VFModalCard',()=>({__esModule:true,default:({children,closeModal}:any)=><div><button onClick={closeModal}>Close</button>{children}</div>}));
jest.mock('ag-charts-react',()=>({AgCharts:jest.fn(()=>null)}));
const props:any={isModalOpen:true,runDate:'07 Apr 2026',rowData:{sku:'sku',wh:'location'},skuKey:'sku',whKey:'wh',monitoringData:[],masterData:{nm:90},suggestionData:[],
 chartData:[{dt:'2026-04-06',stk:7,cs:null,bz:'12',rrs:2},{dt:'2026-04-06',stk:999},{dt:'2025-04-07',stk:8}],
 normChangeData:[{nCD:'2026-04-06',olN:60,nN:90},{nCD:'2026-04-06',olN:90,nN:120}]};
const options=()=> (AgCharts as unknown as jest.Mock).mock.calls.slice(-1)[0][0].options;
beforeEach(()=>jest.clearAllMocks());
it('renders nothing while loading and an explicit error on failure',()=>{
 const view=render(<DailyDataGraphModal {...props} status="loading" />);
 expect(screen.queryByRole('status')).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Close'})).not.toBeInTheDocument();
 expect(AgCharts).not.toHaveBeenCalled();
 view.rerender(<DailyDataGraphModal {...props} status="error" />);
 expect(screen.getByRole('alert')).toHaveTextContent('Unable to load');
 expect(mockDateFetch).not.toHaveBeenCalled();
});
it('preserves default and changed horizon, first duplicate, inherited date matching and norm tie semantics',()=>{
 render(<DailyDataGraphModal {...props} status="ready" />);
 const before=options();
 expect(before.series).toHaveLength(8);
 const stock=before.series.find((s:any)=>s.yKey==='stk').data;
 const norm=before.series.find((s:any)=>s.yKey==='normRed').data;
 expect(stock).toHaveLength(16); // 14 days plus unchanged boundary points
 expect(stock.find((d:any)=>d.dt==='2026-04-06').stk).toBe(7);
 expect(stock.find((d:any)=>d.dt==='2025-04-07').stk).toBe(8); // retained year predicate
 expect(norm.find((d:any)=>d.date==='2026-04-06')).toMatchObject({norm:120,normRed:40,normBlue:12,rrs:2,upwardStockBasedNorm:120});
 expect(norm.find((d:any)=>d.date==='2026-04-05')).toMatchObject({norm:60,normRed:20,normBlue:0});
 fireEvent.change(screen.getByRole('slider'),{target:{value:'30'}});
 const after=options();
 expect(after.series.find((s:any)=>s.yKey==='stk').data).toHaveLength(32);
 expect(after.series.find((s:any)=>s.yKey==='stk').data.slice(-15)).toEqual(stock.slice(1));
 expect(mockDateFetch).not.toHaveBeenCalled();
});
