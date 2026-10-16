// Register the same grid features as the app bootstrap, without importing its persistor.
import 'ag-grid-enterprise';
import { cleanup, render, screen, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { configureStore } from '@reduxjs/toolkit';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import { UserDataContext } from '../../../../../context';
import mtaReducer from '../../../../../redux/reducers/MTA';
import { MTAStore } from '../../../../types/MTA';
import { useGetLastRunDate, useResetState, useSaveState } from '../../../../Services/MTA/SupplyChainIntelligenceHub/BPR';
import { useGetState } from '../../../../Services/MTA/Common/UserUIConfig';
import { useGetUIConfigData } from '../../../../Services/MTA/Common/UIConfig';
import {
  useGetInTransitWhereAboutsData,
  useGetInTransitWhereAboutsDataCount,
  useGetRemarkDetailsForInTransit,
  useSubmitRemarksForInTransit,
  useGetTransporterDetails,
} from '../../../../Services/MTA/Logistics/InTransitWhereAbouts';
import InTransitWhereAbouts from './index';

jest.mock('../../../../Services/MTA/Logistics/InTransitWhereAbouts');
jest.mock('../../../../Services/MTA/SupplyChainIntelligenceHub/BPR');
jest.mock('../../../../Services/MTA/Common/UserUIConfig');
jest.mock('../../../../Services/MTA/Common/UIConfig');

const originalResizeObserver = global.ResizeObserver;
let queryClient: QueryClient;

beforeEach(() => {
  jest.clearAllMocks();
  global.ResizeObserver = class {
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
  };
  queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, cacheTime: 0 } },
  });
  (useGetInTransitWhereAboutsDataCount as jest.Mock).mockReturnValue({
    mutateAsync: jest.fn().mockResolvedValue({ data: { recordCount: '1' } }),
    isLoading: false,
  });
  (useGetInTransitWhereAboutsData as jest.Mock).mockReturnValue({
    mutateAsync: jest.fn().mockResolvedValue({
      data: { data: [{ OrderNo: 'ORDER-RENDER-1', Qty: 12 }] },
    }),
    isLoading: false,
  });
  for (const hook of [useGetRemarkDetailsForInTransit, useSubmitRemarksForInTransit,
    useGetTransporterDetails, useSaveState, useResetState]) {
    (hook as jest.Mock).mockReturnValue({
      mutateAsync: jest.fn().mockResolvedValue({ data: { data: [] } }),
    });
  }
  (useGetState as jest.Mock).mockReturnValue({
    mutateAsync: jest.fn().mockResolvedValue({ data: { data: '' } }),
    isLoading: false,
  });
  (useGetUIConfigData as jest.Mock).mockReturnValue({
    mutateAsync: jest.fn().mockResolvedValue({
      data: { data: [
        { Col_Code: 'OrderNo', Header: 'Order No', Visible: true, DataType: 'String', Col_Position: 1 },
        { Col_Code: 'Qty', Header: 'QTY', Visible: true, DataType: 'String', Col_Position: 2 },
      ] },
    }),
    isLoading: false,
    isError: false,
  });
  (useGetLastRunDate as jest.Mock).mockReturnValue({
    mutateAsync: jest.fn().mockResolvedValue({
      data: { data: [{ formatted: '18 Oct 2026', rawDate: '2026-10-18' }] },
    }),
  });
});

afterEach(() => {
  cleanup();
  queryClient.clear();
  global.ResizeObserver = originalResizeObserver;
});

test('renders the configured transit grid and supplied row with the real MTA reducer', async () => {
  // Exercise real Redux selectors/dispatch without starting the app's encrypted persistor.
  const initialState: MTAStore = {
    showDailyDataGraphModal: false,
    showNormChangeHistoryTable: false,
    dailyData: { normChangeData: [], chartData: [], masterData: [], suggestionData: [],
      monitoringData: [], rowData: {} },
    currentGridState: [],
    planning: { currentTab: '', currentCategory: '', currentView: '' },
    lastRunDate: '',
    EnvConfig: { IN_TRANSIT_WHEREABOUTS_ROWS_PER_PAGE: '100' },
    mtaVFMultiFilter: [],
  };
  const store = configureStore({ reducer: { mta: mtaReducer(initialState) } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/mta/logistics/intransit-whereabouts']}>
        <Provider store={store}>
          <UserDataContext.Provider value={{
            user: { user: { theme_ui: 'NOIRFUSION' } },
            changeColorTheme: color => color,
            isSideBarOpen: true,
            toggleSideBar: jest.fn(),
          }}>
            <InTransitWhereAbouts />
          </UserDataContext.Provider>
        </Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  expect(screen.getByRole('button', { name: 'Add Filter' })).toBeInTheDocument();
  const grid = within(screen.getByRole('treegrid'));
  expect(await grid.findByRole('gridcell', { name: 'ORDER-RENDER-1' })).toBeInTheDocument();
  expect(grid.getByRole('columnheader', { name: 'Order No' })).toBeInTheDocument();
  expect(grid.getByRole('columnheader', { name: 'QTY' })).toBeInTheDocument();
  expect(grid.getByRole('gridcell', { name: '12' })).toBeInTheDocument();
  expect(screen.getByText('18 Oct 2026')).toBeInTheDocument();
  expect(store.getState().mta.lastRunDate).toBe('2026-10-18');
});
