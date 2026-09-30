
import { MaterialRequirementService } from './api';
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


    it('should fetch Material Requirement Daywise', async () => {

        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await MaterialRequirementService.getMaterialRequirementDataDayWise({});
        expect(response.status).toBe(200);
    });

    it('should fetch Material Requirement Cumulative', async () => {
        mockedAxios.put.mockResolvedValueOnce({data:'test',status:200});
      const response = await MaterialRequirementService.getMaterialRequirementData({});
      expect(response.status).toBe(200);
    });


});
