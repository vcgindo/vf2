
import { OrderReschedulingService } from './api';
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


    it('should fetch rm and supplier data', async () => {

        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await OrderReschedulingService.getOrderReschedulingPageData('1', 10, {});
        expect(response.status).toBe(200);
    });


    it('should fetch data with pagination for next page', async () => {

        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200,appliedFilters:'plant' });
        const response = await OrderReschedulingService.getOrderReschedulingPageData('2', 10,'plant');
        expect(response.status).toBe(200);
    });


    it('should update order due date', async () => {

        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await OrderReschedulingService.putUpdateOrderDueDate([{ "unm": "Admin", "isUnSch": 1, "ordData": [{ "ok": "ord 022_1", "r": "" }] }]);
        expect(response).toBe(undefined);
    });





    it('should fetch Material Requirement Cumulative', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: 'test', status: 200 });
        const mockData = [
            {
                "unm": "Admin",
                "isUnSch": 1,
                "ordData": [
                    {
                        "ok": "string",
                        "r": "string"
                    }
                ]
            }
        ]
        const response = await OrderReschedulingService.putUpdateOrderDueDate(mockData);
        expect(response).toBe(undefined);
    });


});
