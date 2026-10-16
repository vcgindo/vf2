import { settleRequestPair } from "./requestPair";

const deferred = <T>() => {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((onResolve, onReject) => {
    resolve = onResolve;
    reject = onReject;
  });
  return { promise, resolve, reject };
};

describe("settleRequestPair", () => {
  it("starts count and grid without waiting for either result", async () => {
    const count = deferred<string>();
    const grid = deferred<string>();
    const started: string[] = [];

    const result = settleRequestPair(
      () => { started.push("count"); return count.promise; },
      () => { started.push("grid"); return grid.promise; }
    );

    expect(started).toEqual(["count", "grid"]);
    grid.resolve("rows");
    count.resolve("42");
    await expect(result).resolves.toEqual({ count: "42", grid: "rows" });
  });

  it("waits for both and gives a count failure precedence", async () => {
    const count = deferred<string>();
    const grid = deferred<string>();
    const countError = new Error("count failed");
    const gridError = new Error("grid failed");
    let settled = false;

    const result = settleRequestPair(() => count.promise, () => grid.promise);
    result.catch(() => { settled = true; });
    grid.reject(gridError);
    await Promise.resolve();
    await Promise.resolve();
    expect(settled).toBe(false);
    count.reject(countError);
    await expect(result).rejects.toBe(countError);
  });

  it("does not publish either result after one request fails", async () => {
    const count = deferred<string>();
    const grid = deferred<string>();
    const published: string[] = [];
    const gridError = new Error("grid failed");

    const result = settleRequestPair(() => count.promise, () => grid.promise)
      .then(({ count: countValue, grid: gridValue }) => {
        published.push(countValue, gridValue);
      });
    grid.reject(gridError);
    count.resolve("42");

    await expect(result).rejects.toBe(gridError);
    expect(published).toEqual([]);
  });

  it("starts grid even when count throws synchronously", async () => {
    const countError = new Error("count failed");
    const grid = jest.fn(async () => "rows");

    await expect(settleRequestPair(
      () => { throw countError; },
      grid
    )).rejects.toBe(countError);
    expect(grid).toHaveBeenCalledTimes(1);
  });
});
