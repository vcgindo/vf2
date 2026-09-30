import axios, { AxiosStatic } from 'axios';
import { getDayWiseCoverageData } from './api';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<AxiosStatic>;

describe('Daywise Coverage', () => {
    const OLD_ENV = process.env;
    beforeEach(() => {
        jest.resetModules() // Most important - it clears the cache
        process.env = { ...OLD_ENV }; // Make a copy
    });
    process.env.REACT_APP_VF_API_HOST_MTO = 'http://10.8.1.10:9000'

    afterEach(() => {
        jest.clearAllMocks();
    });


    it('Should get the data', async () => {

        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await getDayWiseCoverageData("", "", "");
        expect(response.status).toBe(200);
    });
});