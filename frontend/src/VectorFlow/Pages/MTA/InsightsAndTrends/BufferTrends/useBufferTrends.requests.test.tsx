import { act, renderHook } from '@testing-library/react';
import useBufferTrends from './useBufferTrends';

const mockGraph = jest.fn();
jest.mock('../../../../Services/MTA/InsightsAndTrends/BufferTrends', () => ({
  useGetBufferTrendsGraph: () => ({ mutateAsync: mockGraph, isLoading: false }),
}));
jest.mock('../../../../../context', () => ({ useUserData: () => ({ user: { user: { theme_ui: 'NOIRFUSION' } } }) }));
jest.mock('../../../../../hooks/useGetLastRunData', () => () => ({ date: '2026-04-07' }));
jest.mock('../../../../../hooks/useBPRFilter', () => () => ({ state: {}, setState: jest.fn(), onDelete: jest.fn() }));
jest.mock('../../../../../helpers/notify', () => ({ notifyError: jest.fn(), notifySuccess: jest.fn() }));
jest.mock('react-toastify', () => ({ toast: { dismiss: jest.fn() } }));
const deferred = () => {
  let resolve: (v: any) => void = () => {};
  const promise = new Promise(yes => { resolve = yes; });
  return { promise, resolve };
};
const response = (value: number) => ({ data: { data: {
  absolute: [{ date: '06 Apr 2026', b: value, r: 2 }],
  percentage: [{ date: '06 Apr 2026', b: value + 1, r: 3 }],
  summary: [{ sumB: value }], avail: value,
} } });
beforeEach(() => jest.clearAllMocks());

test('newest filter response owns graph, summary and availability; source response stays unchanged', async () => {
  const old = deferred(), next = deferred();
  mockGraph.mockReturnValueOnce(old.promise).mockReturnValueOnce(next.promise);
  const { result } = renderHook(useBufferTrends);
  await act(async () => { result.current.handleApplyFilter({ old: true }); });
  await act(async () => { result.current.handleApplyFilter({ next: true }); });
  const fresh = response(20);
  await act(async () => next.resolve(fresh));
  await act(async () => old.resolve(response(10)));
  expect(result.current.currentGraphData).toEqual([{ date: '06 Apr 2026', b: 20, r: 2, total: '22' }]);
  expect(result.current.summaryData).toEqual([{ sumB: 20 }]);
  expect(result.current.availability).toBe(20);
  expect(fresh.data.data.absolute).toEqual([{ date: '06 Apr 2026', b: 20, r: 2 }]);
});

test('percentage selection during a pending submission uses the new percentage data without another fetch', async () => {
  const pending = deferred();
  mockGraph.mockReturnValue(pending.promise);
  const { result } = renderHook(useBufferTrends);
  await act(async () => { result.current.BufferTrendsDataLoad(); });
  act(() => result.current.onFloatingTabChangeOnPages({ value: 'Percentage' }));
  await act(async () => pending.resolve(response(20)));
  expect(result.current.currentGraphData).toEqual([{ date: '06 Apr 2026', b: 21, r: 3, total: '24' }]);
  expect(mockGraph).toHaveBeenCalledTimes(1);
});

test('changing Tech/Eco invalidates an unfinished result before the next request', async () => {
  const pending = deferred();
  mockGraph.mockReturnValue(pending.promise);
  const { result } = renderHook(useBufferTrends);
  await act(async () => { result.current.BufferTrendsDataLoad(); });
  act(() => result.current.onFloatingTabChange({ value: 'eco' }));
  await act(async () => pending.resolve(response(20)));
  expect(result.current.currentGraphData).toEqual([]);
  expect(result.current.summaryData).toEqual([]);
});

test('clicking the already selected tab does not discard its pending submission', async () => {
  const pending = deferred();
  mockGraph.mockReturnValue(pending.promise);
  const { result } = renderHook(useBufferTrends);
  await act(async () => { result.current.BufferTrendsDataLoad(); });
  act(() => result.current.onFloatingTabChange({ value: 'tech' }));
  await act(async () => pending.resolve(response(20)));
  expect(result.current.availability).toBe(20);
});
