
import { DepartmentWiseBMReport } from './api';
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


    it('should fetch the initial data', async () => {
        process.env.REACT_APP_MTO_BM_REPORT_ROWS_PER_PAGE = '5000';
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const data = { wip: true, curr: 1, appliedFilters: {} };
        const response = await DepartmentWiseBMReport.getFilteredDeptWiseBMReport(data);
        expect(response.status).toBe(200);
        const url = mockedAxios.put.mock.calls[0][0] as string;
        expect(new URL(url, 'http://localhost').searchParams.get('page_size')).toBe('5000');
    });
    
    it('should fetch the initial data', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const data = { wip: false, curr: 1, appliedFilters: {}, page_size: 500};
        const response = await DepartmentWiseBMReport.getFilteredDeptWiseBMReport(data);
        expect(response.status).toBe(200);
    });

    it('should fetch the initial data', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const data = { wip: true, curr: 2, appliedFilters: {ms: ["MTO", "MTA"]} };
        const response = await DepartmentWiseBMReport.getFilteredDeptWiseBMReport(data);
        expect(response.status).toBe(200);
    });
    
    it('should fetch the initial data', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const data = { wip: false, curr: 2, appliedFilters: {ms: ["MTO", "MTA"]} };
        const response = await DepartmentWiseBMReport.getFilteredDeptWiseBMReport(data);
        expect(response.status).toBe(200);
    });

    it('should fetch the bomb level datar', async () => {

        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const data = { wip: true, curr: 1 };
        const response = await DepartmentWiseBMReport.getBombLevelData(data);
        expect(response.status).toBe(200);
    });

  

    it('should make a POST request with the correct URL and body', async () => {
        const mockBody = { department: 'IT', status: 'In Progress' };
        const mockResponse = { data: { success: true, data: [] } };
        // Mock the axios post request
        mockedAxios.post.mockResolvedValue(mockResponse);
        // Call the function
        const response = await DepartmentWiseBMReport.addBMReportRemark(mockBody);
        // Check if axios.post was called with correct URL and body
        expect(axios.post).toHaveBeenCalledWith(
            process.env.REACT_APP_VF_API_HOST_MTO + '/createBMReportRemarksData/',
            mockBody,
            {
                headers: {
                    'Content-Type': 'application/json',
                },
            }
        );

        // Check if the response is correct
        expect(response).toEqual(mockResponse);
        
    });


    it('should call axios.post with correct URL and body', async () => {
        const mockBody = { department: 'IT', status: 'In Progress' };
        const mockResponse = { data: { success: true, data: [] } };
        // Mock the axios post request
        mockedAxios.post.mockResolvedValue(mockResponse);
        // Call the function
        const response = await DepartmentWiseBMReport.getDeptWiseWipData(mockBody);
        // Check if axios.post was called with correct URL and body
        expect(axios.post).toHaveBeenCalledWith(
            process.env.REACT_APP_VF_API_HOST_MTO + '/getDeptWiseWipData/',
            mockBody,
            {
                headers: {
                    'Content-Type': 'application/json',
                },
            }
        );

        // Check if the response is correct
        expect(response).toEqual(mockResponse);
    });


    it('should fetch the High Ageing Data', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const data = { wip: false, curr: 2, appliedFilters: {ms: ["MTO", "MTA"]} };
        const response = await DepartmentWiseBMReport.getHighAgeingData(data);
        expect(response.status).toBe(200);
    });



});
