import { act, renderHook } from '@testing-library/react';
import { GridStateContext } from '../context/GridStateContext';
import useSaveAllState from './useSaveAllState';

const mockSave = jest.fn(), mockReset = jest.fn();
jest.mock('../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR', () => ({
  useSaveState: () => ({ mutateAsync: mockSave }),
  useResetState: () => ({ mutateAsync: mockReset }),
}));
jest.mock('../helpers/notify', () => ({
  notifyError: jest.fn(), notifyLoader: jest.fn(), notifySuccess: jest.fn(),
}));

const api = () => ({
  isDestroyed: jest.fn(() => false),
  getColumnState: jest.fn(() => [{ colId: 'OrderNo', hide: false }]),
  getChartModels: jest.fn(() => []), isPivotMode: jest.fn(() => false),
  applyColumnState: jest.fn(), restoreChart: jest.fn(), setGridOption: jest.fn(),
  resetColumnState: jest.fn(),
});
const pending = () => {
  let resolve!: (value?: any) => void;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
};
beforeEach(() => jest.clearAllMocks());

test('saving a live layout persists and restores the captured layout', async () => {
  mockSave.mockResolvedValue({});
  const current = api();
  const ref = { current: { api: current } };
  const wrapper = ({ children }: any) => <GridStateContext.Provider value={{ ref } as any}>{children}</GridStateContext.Provider>;
  const { result } = renderHook(() => useSaveAllState(), { wrapper });
  await act(async () => { await result.current.onSaveState('InTransitWhereabouts'); });
  expect(mockSave).toHaveBeenCalledWith({ reportname: 'InTransitWhereabouts', state: JSON.stringify({
    pivot: false, charts: [], columns: [{ colId: 'OrderNo', hide: false }],
  }) });
  expect(current.applyColumnState).toHaveBeenCalledWith({ state: [{ colId: 'OrderNo', hide: false }] });
  expect(current.setGridOption).toHaveBeenCalledWith('pivotMode', false);
});

test('a saved response cannot apply the old layout to a replacement grid', async () => {
  const deferred = pending(); mockSave.mockReturnValue(deferred.promise);
  const first = api(), second = api();
  const ref = { current: { api: first } };
  const wrapper = ({ children }: any) => <GridStateContext.Provider value={{ ref } as any}>{children}</GridStateContext.Provider>;
  const { result } = renderHook(() => useSaveAllState(), { wrapper });
  let saving!: Promise<void>;
  act(() => { saving = result.current.onSaveState('BPR'); });
  ref.current = { api: second };
  first.isDestroyed.mockReturnValue(true);
  await act(async () => { deferred.resolve(); await saving; });
  expect(first.applyColumnState).not.toHaveBeenCalled();
  expect(second.applyColumnState).not.toHaveBeenCalled();
});

test('reset completion after grid destruction performs no grid mutation or resave', async () => {
  const deferred = pending(); mockReset.mockReturnValue(deferred.promise);
  const current = api(), resetCallback = jest.fn();
  const ref = { current: { api: current } };
  const wrapper = ({ children }: any) => <GridStateContext.Provider value={{ ref, onResetCallback: resetCallback } as any}>{children}</GridStateContext.Provider>;
  const { result } = renderHook(() => useSaveAllState(), { wrapper });
  let resetting!: Promise<void>;
  act(() => { resetting = result.current.onResetAllState('BPR'); });
  current.isDestroyed.mockReturnValue(true);
  await act(async () => { deferred.resolve(); await resetting; });
  expect(resetCallback).not.toHaveBeenCalled();
  expect(current.applyColumnState).not.toHaveBeenCalled();
  expect(current.resetColumnState).not.toHaveBeenCalled();
  expect(mockSave).not.toHaveBeenCalled();
});
