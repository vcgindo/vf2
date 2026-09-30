
import { UserUIConfigService } from './api';
import axios, { AxiosStatic } from 'axios';

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


    it('should fetch User uiconfig data', async () => {

        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await UserUIConfigService.getState( {un: 'test', rn_id: 1})
        expect(response.status).toBe(200);
    });

    it('should Update User uiconfig data', async () => {

        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await UserUIConfigService.saveState( {reportname: 'test', state: "test config"})
        expect(response.status).toBe(200);
    });
    
    it('should Update User uiconfig data', async () => {

        const mockBody =  {reportname: 'test', state: "test config"};
        const mockResponse = { data: { success: true } };
        mockedAxios.put.mockResolvedValue(mockResponse);
        const result = await UserUIConfigService.saveState(mockBody);
        expect(mockedAxios.put).toHaveBeenCalledWith(
            `${process.env.REACT_APP_VF_API_HOST_MTO}/UpdateUserwiseUIReportConfigurationData/`,
            mockBody,
            { headers: { 'Content-Type': 'application/json' } }
        );
        expect(result).toEqual(mockResponse);
    });

});