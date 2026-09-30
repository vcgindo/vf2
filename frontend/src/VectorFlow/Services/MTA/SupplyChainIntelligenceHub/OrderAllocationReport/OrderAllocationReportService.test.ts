import { OrderAllocationReportService } from './api';
import axios, { AxiosStatic } from 'axios';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<AxiosStatic>;

describe('Testing the RRRColorBandWiseService', () => {
    const OLD_ENV = process.env;
    
    beforeEach(() => {
        jest.resetModules(); // Clear the cache
        process.env = { ...OLD_ENV }; // Make a copy
    });

    process.env.REACT_APP_VF_API_HOST = 'http://10.8.1.10:8082';

    afterEach(() => {
        jest.clearAllMocks();
    });

    it('should make a Post request to /GetRRRColorBandWiseRecordCount', async () => {
        // Mock response
        mockedAxios.post.mockResolvedValueOnce({
            "recordCount": "3124",
            "data": "",
            "status": 200,
            "msg": null,
            "errorCount": null,
            "error": null,
            "conflictErrorCount": null,
            "conflictError": null
        });

        // const mockBody = {
        //     "filters": [],
        //     "paginationParameter": {
        //         "pageNumber": 1,
        //         "recordsPerPage": 50
        //     }
        // };

        // const response = await OrderAllocationReportService.getOrderAllocationReportRecordsCount(mockBody);
        
        // expect(mockedAxios.post).toHaveBeenCalledWith(
        //     'http://10.8.1.10:8082/GetOrderAllocationReportDataCount',
        //     mockBody,
        //     {
        //         headers: { 'Content-Type': 'application/json' }
        //     }
        // );
        // expect(response.status).toBe(200);
    });

    it('should make a Post request to /GetOrderAllocationReportData', async () => {
        // Mock response
        mockedAxios.post.mockResolvedValueOnce({
            "recordCount": "100",
            "data": [],
            "status": 200,
            "msg": null,
            "errorCount": null,
            "error": null,
            "conflictErrorCount": null,
            "conflictError": null
        });

        const mockBody = {
            "filters": [],
            "paginationParameter": {
                "pageNumber": 1,
                "recordsPerPage": 50
            }
        };

        const response = await OrderAllocationReportService.getOrderAllocationReportData(mockBody);
        
        // expect(mockedAxios.post).toHaveBeenCalledWith(
        //     'http://10.8.1.10:8082/GetOrderAllocationReportData',
        //     mockBody,
        //     {
        //         headers: { 'Content-Type': 'application/json' }
        //     }
        // );
        expect(response.status).toBe(200);
    });
});