
import { RMPMExpedtingServices } from './api';
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


    it('should fetch rm and supplier data', async () => {

        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const data = { val: 'all', horizon: 7, appliedFilters: {} };
        const response = await RMPMExpedtingServices.getRMPMExpedition(data);
        expect(response.status).toBe(200);
    });

    it('should fetch rm data ', async () => {

        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const data = { val: 'rm', horizon: 7, appliedFilters: {}  };
        const response = await RMPMExpedtingServices.getRMPMExpedition(data);
        expect(response.status).toBe(200);
    });

    it('should fetch supplier data ', async () => {

        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const data = { val: 'supplier', horizon: 7, appliedFilters: {}  };
        const response = await RMPMExpedtingServices.getRMPMExpedition(data);
        expect(response.status).toBe(200);
    });

    it('should fetch Material Requirement Cumulative', async () => {
        mockedAxios.get.mockResolvedValueOnce({data:'test',status:200});
      const response = await RMPMExpedtingServices.getLastRunDate();
      expect(response.status).toBe(200);
    });


});