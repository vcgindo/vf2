
import { ReasonOrderChangeServices } from './api';
import axios, { AxiosStatic } from 'axios';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<AxiosStatic>;

describe('MaterialRequirement', () => {
    const OLD_ENV = process.env;
    beforeEach(() => {
        jest.resetModules() // Most important - it clears the cache
        process.env = { ...OLD_ENV }; // Make a copy
    });
    process.env.REACT_APP_VF_API_HOST_MTO = 'http://10.8.1.10:8000'

    afterEach(() => {
        jest.clearAllMocks();
    });


    it('should fetch the data for Analytical screen ', async () => {

        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await ReasonOrderChangeServices.getPoogiReasonsAnalyticalData();
        expect(response.status).toBe(200);
    });

    it('should fetch Poogi Reason for Delayed Order', async () => {

        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const data = { wip: 1, curr: 1, appliedFilters: {}, pageSize: 10 };
        const response = await ReasonOrderChangeServices.getPoogiReasonsDelayedOrder(data);
        expect(response.status).toBe(200);
    });

    it('should fetch Poogi Remarks', async () => {

        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const data = { ok: 'Ord3 001' };
        const response = await ReasonOrderChangeServices.getPoogIRemarks(data.ok);
        expect(response.status).toBe(200);
    });

    it('should fetch Poogi Major and Minor Reasons', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await ReasonOrderChangeServices.getPoogiMajorMinorReason();
        expect(response.status).toBe(200);
    });

    it('should make a PUT request with the correct URL and body', async () => {
        const mockBody = { reason: 'Test reason' };
        const mockResponse = { data: { success: true } };
        mockedAxios.put.mockResolvedValue(mockResponse);
        const result = await ReasonOrderChangeServices.updatePoogiRemarks(mockBody);
        expect(mockedAxios.put).toHaveBeenCalledWith(
            `${process.env.REACT_APP_VF_API_HOST_MTO}/updatePoogiReasonsforOrders/`,
            mockBody,
            { headers: { 'Content-Type': 'application/json' } }
        );
        expect(result).toEqual(mockResponse);
    });


});