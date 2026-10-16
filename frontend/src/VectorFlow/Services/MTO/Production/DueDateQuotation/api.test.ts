import { DueDateQuotationService } from './api';
import axios, { AxiosStatic } from 'axios';
 
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
 
    it('should UIConfig for DDQ', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DueDateQuotationService.getUIConfig("DueDateQuotation");
        expect(response.status).toBe(200);
    });
 
    it('should get orders for DDQ for Unscheduled Order  without filters', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DueDateQuotationService.getFilteredOrdersForDDQ({page: 1, unSch: true});
        expect(response?.status).toBe(200);
    });
    
    it('should get orders for DDQ for Scheduled Order  without filters', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DueDateQuotationService.getFilteredOrdersForDDQ({page: 1, unSch: false});
        expect(response?.status).toBe(200);
    });
 
    it('should get orders for DDQ for Unscheduled Order  with Filters', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DueDateQuotationService.getFilteredOrdersForDDQ({page: 1, unSch: true, appliedFilters:{
            "ms": [
              "MTO",
              "MTA"
            ]
          } });
        expect(response?.status).toBe(200);
    });

    it('should get orders for DDQ for Scheduled Order with Filters', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DueDateQuotationService.getFilteredOrdersForDDQ({page: 1, unSch: false, appliedFilters:{
            "ms": [
              "MTO",
              "MTA"
            ]
          }
        });
        expect(response?.status).toBe(200);
    });
 
    it('should get Buffer Master Data', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DueDateQuotationService.getBufferMasterData();
        expect(response.status).toBe(200);
    });
 
    it('should get CCR master group', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DueDateQuotationService.getCCRGroupMaster();
        expect(response.status).toBe(200);
    });
 
    it('should get Route Details', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DueDateQuotationService.getRouteDetails(1);
        expect(response.status).toBe(200);
    });
 
    it('should get CCRItemTypeMapping Master', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DueDateQuotationService.getCCRItemTypeMappingMaster();
        expect(response.status).toBe(200);
    });
 
    it('should get FOL Data', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DueDateQuotationService.getFOLData();
        expect(response.status).toBe(200);
    });
 
    it('should get CCR Master Data', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DueDateQuotationService.getCCRMasterData();
        expect(response.status).toBe(200);
    });
 
    it('should get Line CCR Master Data', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DueDateQuotationService.getLineCCRDetails(['3']);
        expect(response).toBe(undefined);
    });
 
    it('should get DailyWorking Calendar', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DueDateQuotationService.getDailyWorkingCalendar();
        expect(response.status).toBe(200);
    });
 
    it('should get MarketOperatingLeadTimeMaster Data', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DueDateQuotationService.getMarketOperatingLeadTimeMasterData();
        expect(response.status).toBe(200);
    });
 
    it('should get Line CCR Master Data', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DueDateQuotationService.getLineCCRDetails(['3']);
        expect(response).toBe(undefined);
    });
 
    it('should update updateBuffRouteCCREstDate', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DueDateQuotationService.updateBuffRouteCCREstDate({ bufferData: [""], routeData: [""] });
        expect(response.status).toBe(200);
    });
 
    it('should update updateScheduleOrders', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DueDateQuotationService.updateScheduleOrders({ orders: [""] });
        expect(response.status).toBe(200);
    });

});
 
