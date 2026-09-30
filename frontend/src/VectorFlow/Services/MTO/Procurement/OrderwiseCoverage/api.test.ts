
import { OrderwiseCoverageService } from './api';
import axios, { AxiosStatic } from 'axios';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<AxiosStatic>;

describe('OrderwiseCoverage', () => {
    const OLD_ENV = process.env;
    beforeEach(() => {
        jest.resetModules() // Most important - it clears the cache
        process.env = { ...OLD_ENV }; // Make a copy
    });
    process.env.REACT_APP_VF_API_HOST_MTO = 'http://10.8.1.10:9000'

    afterEach(() => {
        jest.clearAllMocks();
    });



    it('should get orderwisedata data', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await OrderwiseCoverageService.getOrderwiseCoverageData({ graph: 1 });
        expect(response.status).toBe(200);
    });

    it('should get orderwisedata data', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await OrderwiseCoverageService.getOrderwiseCoverageData({ page: 1, graph: 0, appliedFilters: {} });
        expect(response.status).toBe(200);
    });

});
