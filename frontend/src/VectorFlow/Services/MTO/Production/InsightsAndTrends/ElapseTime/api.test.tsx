import axios, { AxiosStatic } from 'axios';
import { getElapsedDaysforDeptPlantData, getElapsedTimeData } from './api';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<AxiosStatic>;

describe('UIConvfig Service', () => {
    const OLD_ENV = process.env;
    beforeEach(() => {
        jest.resetModules() // Most important - it clears the cache
        process.env = { ...OLD_ENV }; // Make a copy
    });
    process.env.REACT_APP_VF_API_HOST_MTO = 'http://10.8.1.10:9000'

    afterEach(() => {
        jest.clearAllMocks();
    });

    it('getElapsedDaysforDeptPlantData', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await getElapsedDaysforDeptPlantData(1, 0)
        expect(response.status).toBe(200);
    });

    it('getElapsedTimeData', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await getElapsedTimeData({ page: 1, graphflag: 0, appliedFilters: {} })
        expect(response.status).toBe(200);
    });
   
    it('getElapsedTimeData', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await getElapsedTimeData({ graphflag: 1})
        expect(response.status).toBe(200);
    });

});