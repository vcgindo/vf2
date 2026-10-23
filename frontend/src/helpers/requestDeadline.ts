// Deadlines settle the client wait; they do not retry or undo a server action.
export const REQUEST_TIMEOUT_MS = 60_000;
export const DOWNLOAD_TIMEOUT_MS = 10 * 60_000;

export const createRequestDeadline = (milliseconds = REQUEST_TIMEOUT_MS) => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), milliseconds);
  return { signal: controller.signal, finish: () => clearTimeout(timer) };
};
