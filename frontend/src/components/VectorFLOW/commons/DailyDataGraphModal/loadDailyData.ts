import { nanoid } from '@reduxjs/toolkit';
import { format, parseISO } from 'date-fns';
import { RESOLVE_DAILY_DATA, TOGGLE_GRAPH_MODAL, UPDATE_DAILY_DATA } from '../../../../redux/actions/MTA';
import { DailyDataGraph } from '../../../../VectorFlow/types/MTA';

// Request identity belongs to the existing modal state. Closing invalidates it;
// a subsequent selection replaces it before either network response can finish.
export async function loadDailyData(dispatch: any, getDailyData: any, rowData: any, whKey: string, skuKey = 'SKUCode') {
  const pending: DailyDataGraph = {
    requestId: nanoid(), status: 'loading', rowData,
    chartData: [], normChangeData: [], masterData: undefined,
    suggestionData: [], monitoringData: [],
  };
  dispatch(TOGGLE_GRAPH_MODAL(false));
  dispatch(UPDATE_DAILY_DATA(pending));
  try {
    const result = await getDailyData({ SKUCode: rowData[skuKey], WHCode: rowData[whKey] });
    const data = result.data.data[0];
    // Date-only parsing retains the local calendar semantics of GetLastRunDate.
    const runDate = format(parseISO(data.RunDate), 'dd MMM yyyy');
    dispatch(RESOLVE_DAILY_DATA({
      ...pending, status: 'ready', runDate,
      chartData: data.StockData || [], normChangeData: data.NormChangeHistoryData || [],
      masterData: data.MasterData?.[0], suggestionData: data.SuggestionHistoryData || [],
      monitoringData: data.MonitoringData,
    }));
  } catch {
    dispatch(RESOLVE_DAILY_DATA({ ...pending, status: 'error' }));
  }
}
