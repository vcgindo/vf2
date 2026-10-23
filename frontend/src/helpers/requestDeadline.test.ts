import { createRequestDeadline, REQUEST_TIMEOUT_MS, DOWNLOAD_TIMEOUT_MS } from './requestDeadline';
import { errorMessage } from './notify';

beforeEach(() => jest.useFakeTimers());
afterEach(() => jest.useRealTimers());

test('a pending operation aborts at its deadline', () => {
  const request = createRequestDeadline();
  jest.advanceTimersByTime(REQUEST_TIMEOUT_MS - 1);
  expect(request.signal.aborted).toBe(false);
  jest.advanceTimersByTime(1);
  expect(request.signal.aborted).toBe(true);
});

test('finishing one operation leaves another operation deadline intact', () => {
  const finished = createRequestDeadline();
  const pending = createRequestDeadline();
  finished.finish();
  jest.advanceTimersByTime(REQUEST_TIMEOUT_MS);
  expect(finished.signal.aborted).toBe(false);
  expect(pending.signal.aborted).toBe(true);
});

test('download deadline remains active through a long body read', () => {
  const request = createRequestDeadline(DOWNLOAD_TIMEOUT_MS);
  jest.advanceTimersByTime(REQUEST_TIMEOUT_MS);
  expect(request.signal.aborted).toBe(false);
  request.finish();
  jest.advanceTimersByTime(DOWNLOAD_TIMEOUT_MS);
  expect(request.signal.aborted).toBe(false);
});

test('errors render useful text instead of an object', () => {
  expect(errorMessage('No records')).toBe('No records');
  expect(errorMessage(new Error('Request unavailable'))).toBe('Request unavailable');
  expect(errorMessage({ response: { data: { detail: 'Access denied' } } })).toBe('Access denied');
  expect(errorMessage({})).toMatch(/could not be completed/);
});
