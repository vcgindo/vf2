import axios, { AxiosStatic } from 'axios';
import { FullKitAssignmentService } from './api';
 
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<AxiosStatic>;
 
describe('OrderRescheduling', () => {
    const OLD_ENV = process.env;
    beforeEach(() => {
        jest.resetModules() // Most important - it clears the cache
        process.env = { ...OLD_ENV }; // Make a copy
    });
    process.env.REACT_APP_VF_API_HOST_MTO = 'http://10.8.1.10:9000'
 
    afterEach(() => {
        jest.clearAllMocks();
    });
 
    it('should get orders from getFullKitAssignmentDataWithGraphData api', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await FullKitAssignmentService.getFullKitAssignmentDataWithGraphData( true, true, true, 1,1 ,{});
        expect(response.status).toBe(200);
    });
 
    it('should exclude updateExcludedOrdersForFullkitAssignment api', async () => {
        mockedAxios.post.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await FullKitAssignmentService.updateExcludedOrdersForFullkitAssignment([{on:"1", lid:"1"}], "rohan");
        expect(response.status).toBe(200);
    });
 
    it('should simulate orders from updateOrSimulateStockAllocation api', async () => {
        mockedAxios.post.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await FullKitAssignmentService.updateOrSimulateStockAllocation(true,"rohan");
        console.log(response)
        expect(response.status).toBe(200);
    });
 
    it('should get Buffer Master Data', async () => {
        mockedAxios.post.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await FullKitAssignmentService.updateFullkitOnSimulation("Save", "rohan");
        expect(response.status).toBe(200);
    });
});
 