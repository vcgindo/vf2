import { withLoading } from './withLoading';

function deferred() {
  let resolve!: () => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<void>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

it('releases loading and preserves a successful result', async () => {
  const setLoading = jest.fn();
  await expect(withLoading(setLoading, async () => 'data')).resolves.toBe('data');
  expect(setLoading.mock.calls).toEqual([[true], [false]]);
});

it('releases loading and preserves the rejection', async () => {
  const setLoading = jest.fn();
  const error = new Error('request failed');
  await expect(withLoading(setLoading, async () => { throw error; })).rejects.toBe(error);
  expect(setLoading.mock.calls).toEqual([[true], [false]]);
});

it('releases loading when an operation throws before returning a promise', async () => {
  const setLoading = jest.fn();
  const error = new Error('failed to start');
  await expect(withLoading(setLoading, () => { throw error; })).rejects.toBe(error);
  expect(setLoading.mock.calls).toEqual([[true], [false]]);
});

it('keeps a shared indicator active until overlapping operations settle', async () => {
  const setLoading = jest.fn();
  const first = deferred();
  const second = deferred();
  const firstLoad = withLoading(setLoading, () => first.promise);
  const secondLoad = withLoading(setLoading, () => second.promise);
  first.resolve();
  await firstLoad;
  expect(setLoading).not.toHaveBeenCalledWith(false);
  const rejection = expect(secondLoad).rejects.toThrow('timeout');
  second.reject(new Error('timeout'));
  await rejection;
  expect(setLoading).toHaveBeenLastCalledWith(false);
  expect(setLoading.mock.calls.filter(([value]) => !value)).toHaveLength(1);
});

it('settles unrelated indicators independently', async () => {
  const firstSetter = jest.fn();
  const secondSetter = jest.fn();
  const pending = deferred();
  const firstLoad = withLoading(firstSetter, () => pending.promise);
  await withLoading(secondSetter, async () => undefined);
  expect(secondSetter).toHaveBeenLastCalledWith(false);
  expect(firstSetter).not.toHaveBeenCalledWith(false);
  pending.resolve();
  await firstLoad;
  expect(firstSetter).toHaveBeenLastCalledWith(false);
});
