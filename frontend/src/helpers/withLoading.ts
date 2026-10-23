type LoadingSetter = (loading: boolean) => void;

const pendingLoads = new WeakMap<LoadingSetter, number>();

/** Keep a shared loading indicator active until all of its operations settle. */
export async function withLoading<T>(
  setLoading: LoadingSetter,
  operation: () => Promise<T>
): Promise<T> {
  pendingLoads.set(setLoading, (pendingLoads.get(setLoading) || 0) + 1);
  setLoading(true);
  try {
    return await operation();
  } finally {
    const remaining = (pendingLoads.get(setLoading) || 1) - 1;
    if (remaining > 0) {
      pendingLoads.set(setLoading, remaining);
    } else {
      pendingLoads.delete(setLoading);
      setLoading(false);
    }
  }
}
