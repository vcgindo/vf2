
import { OrderAtRiskService } from './api';
import axios, { AxiosStatic } from 'axios';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<AxiosStatic>;

describe('MaterialRequirement', () => {
    const OLD_ENV = process.env;
    beforeEach(() => {
        jest.resetModules()
        process.env = { ...OLD_ENV }; 
    });
    process.env.REACT_APP_VF_API_HOST_MTO = 'http://10.8.1.10:9000'

    afterEach(() => {
        jest.clearAllMocks();
    });

    it('should fetch Order At Risk data ', async () => {

        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await OrderAtRiskService.getOrderAtRiskData({appliedFilters: {}});
        expect(response.status).toBe(200);
    });
});