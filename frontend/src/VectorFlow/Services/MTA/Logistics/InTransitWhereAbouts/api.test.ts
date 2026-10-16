import axios from 'axios';
import { InTransitWhereAboutsService as service } from './api';

jest.mock('axios');
const post = axios.post as jest.Mock;
const previousHost = process.env.REACT_APP_API_HOST;
const cases: Array<[string, (body: any) => Promise<any>, boolean]> = [
  ['GetInTransitWhereAboutsDataCount', service.getInTransitWhereAboutsDataCount, false],
  ['GetInTransitWhereAboutsData', service.getInTransitWhereAboutsData, false],
  ['GetRemarkDetailsForInTransit', service.getRemarkDetailsForInTransit, true],
  ['SubmitRemarksForInTransit', service.submitRemarksForInTransit, true],
  ['GetTransporterDetails', service.getTransporterDetails, false],
];

beforeEach(() => {
  process.env.REACT_APP_API_HOST = '/';
  post.mockResolvedValue({ status: 200, data: [] });
});
afterEach(() => jest.clearAllMocks());
afterAll(() => {
  if (previousHost === undefined) delete process.env.REACT_APP_API_HOST;
  else process.env.REACT_APP_API_HOST = previousHost;
});

it.each(cases)('%s stays on the authenticated local gateway', async (endpoint, invoke, forwardUsers) => {
  const body = { orderNo: 'retained-target', data: [] };
  await invoke(body);
  expect(post).toHaveBeenCalledWith(`/api/mta/${endpoint}`,
    forwardUsers ? { ...body, forwardUsers: true } : body,
    { headers: { 'Content-Type': 'application/json' } });
  const destination = new URL(post.mock.calls[0][0], 'http://127.0.0.1:3006');
  expect(destination.origin).toBe('http://127.0.0.1:3006');
});
