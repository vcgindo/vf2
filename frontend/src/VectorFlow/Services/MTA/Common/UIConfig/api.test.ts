
import { UIConfigService } from './api';
import axios, { AxiosStatic } from 'axios';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<AxiosStatic>;

describe('UIConvfig Service', () => {
    const OLD_ENV = process.env;
    beforeEach(() => {
        jest.resetModules() // Most important - it clears the cache
        process.env = { ...OLD_ENV }; // Make a copy
    });
    process.env.REACT_APP_VF_API_HOST_MTO = 'http://10.8.1.10:9000/api/mto'

    afterEach(() => {
        jest.clearAllMocks();
    });


    it('should fetch uiconfig data', async () => {

        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await UIConfigService.getUIConfigData("EnquiryResponse")
        expect(response.status).toBe(200); 
    }); 

    it('should fetch uiconfig data for BM Report', async () => {

        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await UIConfigService.getUIConfigData("BMReport");
        expect(response.status).toBe(200); 
    }); 

});