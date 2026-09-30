
import { OrderBalanceService } from './api';
import axios, { AxiosStatic } from 'axios';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<AxiosStatic>;

describe('Order Balance Service', () => {
    const OLD_ENV = process.env;
    beforeEach(() => {
        jest.resetModules() // Most important - it clears the cache
        process.env = { ...OLD_ENV }; // Make a copy
    });
    process.env.REACT_APP_VF_API_HOST_MTO = 'http://10.8.1.10:9000'

    afterEach(() => {
        jest.clearAllMocks();
    });

    it('should fetch Order Balance data', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await OrderBalanceService.getOrderBalanceData({graphflag: 1})
        expect(response.status).toBe(200);
    });
    
    it('should fetch Order Balance data', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await OrderBalanceService.getOrderBalanceData({graphflag: 0, page: 1, appliedFilters: {}})
        expect(response.status).toBe(200);
    });

    it('should fetch Order Type Options', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await OrderBalanceService.getOrderTypeOptions()
        expect(response.status).toBe(200);
    });

});