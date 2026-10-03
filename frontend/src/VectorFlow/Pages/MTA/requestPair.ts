export type RequestPair<TCount, TGrid> = {
  count: TCount;
  grid: TGrid;
};

const invoke = <T>(request: () => Promise<T>): Promise<T> => {
  try {
    return Promise.resolve(request());
  } catch (error) {
    return Promise.reject(error);
  }
};

/** Start both independent reads and settle both before returning or failing. */
export const settleRequestPair = async <TCount, TGrid>(
  countRequest: () => Promise<TCount>,
  gridRequest: () => Promise<TGrid>
): Promise<RequestPair<TCount, TGrid>> => {
  const countPromise = invoke(countRequest);
  const gridPromise = invoke(gridRequest);
  const [count, grid] = await Promise.allSettled([countPromise, gridPromise]);

  // Preserve the original sequential flows' count-error precedence.
  if (count.status === "rejected") throw count.reason;
  if (grid.status === "rejected") throw grid.reason;
  return { count: count.value, grid: grid.value };
};
