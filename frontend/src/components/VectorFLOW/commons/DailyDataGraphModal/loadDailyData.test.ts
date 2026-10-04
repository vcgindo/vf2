import { configureStore } from '@reduxjs/toolkit';
import mtaReducer from '../../../../redux/reducers/MTA';
import { TOGGLE_GRAPH_MODAL } from '../../../../redux/actions/MTA';
import { loadDailyData } from './loadDailyData';

const makeStore = () => configureStore({ reducer: mtaReducer({showDailyDataGraphModal:false, dailyData:{}} as any) });
const response = (stock:number) => ({data:{data:[{RunDate:'2026-04-07', StockData:[{stk:stock}], MasterData:[{nm:3}]}]}});
const deferred = () => { let resolve:any; let reject:any; const promise = new Promise((yes,no)=>{resolve=yes;reject=no;}); return {promise,resolve,reject}; };

it('keeps the modal closed until its response and date are ready', async () => {
  const store=makeStore(); const request=deferred(); const fetch=jest.fn(()=>request.promise);
  const pending=loadDailyData(store.dispatch,fetch,{SKUCode:'sku',LocCode:'loc'},'LocCode');
  expect(store.getState().showDailyDataGraphModal).toBe(false);
  expect(store.getState().dailyData.status).toBe('loading');
  expect(store.getState().dailyData.chartData).toEqual([]);
  expect(fetch).toHaveBeenCalledWith({SKUCode:'sku',WHCode:'loc'});
  request.resolve(response(7)); await pending;
  expect(store.getState().showDailyDataGraphModal).toBe(true);
  expect(store.getState().dailyData).toMatchObject({status:'ready',runDate:'07 Apr 2026',chartData:[{stk:7}]});
});
it('does not reopen or populate a closed modal', async () => {
  const store=makeStore(); const request=deferred();
  const pending=loadDailyData(store.dispatch,()=>request.promise,{},'WhCode');
  store.dispatch(TOGGLE_GRAPH_MODAL(false)); request.resolve(response(7)); await pending;
  expect(store.getState().showDailyDataGraphModal).toBe(false);
  expect(store.getState().dailyData.chartData).toEqual([]);
});
it('retains a newer selection when an older request completes last', async () => {
  const store=makeStore(); const old=deferred(); const recent=deferred();
  const a=loadDailyData(store.dispatch,()=>old.promise,{SKUCode:'old'},'WhCode');
  const b=loadDailyData(store.dispatch,()=>recent.promise,{SKUCode:'new'},'WhCode');
  recent.resolve(response(2)); await b; old.resolve(response(1)); await a;
  expect(store.getState().dailyData).toMatchObject({rowData:{SKUCode:'new'},chartData:[{stk:2}]});
});
it('reports failure without retaining a previous graph', async () => {
  const store=makeStore();
  await loadDailyData(store.dispatch,()=>Promise.reject(new Error('unavailable')),{},'LocCode');
  expect(store.getState().dailyData).toMatchObject({status:'error',chartData:[]});
});
