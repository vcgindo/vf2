import { act, renderHook } from '@testing-library/react';
import useLiveGrid, { isLiveGrid } from './useLiveGrid';

const grid = () => ({ isDestroyed: jest.fn(() => false) } as any);

test('a replaced grid cannot clear its live successor through a late destroy event', () => {
  const { result } = renderHook(useLiveGrid);
  const first = grid(), second = grid();
  act(() => result.current.onGridReady({ api: first }));
  act(() => result.current.onGridReady({ api: second }));
  act(() => result.current.onGridPreDestroyed({ api: first }));
  expect(result.current.api).toBe(second);
  act(() => result.current.onGridPreDestroyed({ api: second }));
  expect(result.current.api).toBeUndefined();
});

test('destroyed APIs and late callbacks after unmount are never retained', () => {
  const { result, unmount } = renderHook(useLiveGrid);
  const destroyed = grid();
  destroyed.isDestroyed.mockReturnValue(true);
  act(() => result.current.onGridReady({ api: destroyed }));
  expect(result.current.api).toBeUndefined();
  expect(isLiveGrid(destroyed)).toBe(false);
  const live = grid();
  const ready = result.current.onGridReady;
  unmount();
  expect(result.current.mounted.current).toBe(false);
  ready({ api: live });
  expect(result.current.api).toBeUndefined();
});
