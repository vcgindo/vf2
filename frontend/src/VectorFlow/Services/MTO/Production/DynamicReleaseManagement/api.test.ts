import { DynamicReleaseManagementService } from './api';
import axios, { AxiosStatic } from 'axios';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<AxiosStatic>;

// eslint-disable-next-line
describe('Dynamic Release Service', () => {
    const OLD_ENV = process.env;
    const dummyData = {
        "routeData": {
            "orders": [
                {
                    "route": "string",
                    "ok": "string",
                    "ccrdetails": [
                        {
                            "ccrid": 0,
                            "ccrgrp": 0,
                            "pcQty": 0,
                            "pos": "string",
                            "ol": "string"
                        }
                    ]
                }
            ]
        }
    };

    const appliedFilters = {
        ms: ['MTO', 'MTA']
    }

    const dummyReleaseData = [
        "ord 024_1"
    ];

    beforeEach(() => {
        jest.resetModules(); // Clears the cache
        process.env = { ...OLD_ENV }; // Make a copy
        process.env.REACT_APP_VF_API_HOST_MTO = 'http://10.8.1.10:9000';
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    it('should get orders for DRM for Order for table', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DynamicReleaseManagementService.getDynamicReleaseData({ graph: 0, ao: 0, page: 1, appliedFilters });
        expect(response.status).toBe(200);
    });

    it('should get orders for DRM for Order for graph', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DynamicReleaseManagementService.getDynamicReleaseData({ graph: 1, ao: 0, page: 1, appliedFilters });
        expect(response.status).toBe(200);
    });

    it('should get orders for DRM for Order for graph with a different page', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DynamicReleaseManagementService.getDynamicReleaseData({ graph: 1, ao: 0, page: 2, appliedFilters });
        expect(response.status).toBe(200);
    });

    it('should get orders for DRM for All Orders for graph', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DynamicReleaseManagementService.getDynamicReleaseData({ graph: 1, ao: 1, page: 1, appliedFilters });
        expect(response.status).toBe(200);
    });

    it('should get orders for DRM when ao is not 0', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DynamicReleaseManagementService.getDynamicReleaseData({ graph: 0, ao: 1, page: 1, appliedFilters });
        expect(response.status).toBe(200);
    });
    it('should get orders for DRM when wrong values', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DynamicReleaseManagementService.getDynamicReleaseData({ graph: 3, ao: 3, page: 3, appliedFilters });
        expect(response.status).toBe(200);
    });

    it('should get orders for DRM when page is not 1', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DynamicReleaseManagementService.getDynamicReleaseData({ graph: 0, ao: 0, page: 2, appliedFilters });
        expect(response.status).toBe(200);
    });


    it('should handle a failed API request gracefully', async () => {
        mockedAxios.put.mockRejectedValueOnce(new Error('Network Error'));
        await expect(DynamicReleaseManagementService.getDynamicReleaseData({ graph: 1, ao: 1, page: 1, appliedFilters })).rejects.toThrow('Network Error');
    });

    it('should save the route', async () => {
        mockedAxios.post.mockResolvedValueOnce({ status: 200 });
        const response = await DynamicReleaseManagementService.saveRouteData(dummyData);
        expect(response).toBe(undefined);
    });

    it('should release the selected orders', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await DynamicReleaseManagementService.updateDynamicReleaseData(dummyReleaseData);
        expect(response.status).toBe(200);
    });

    // it('should get orders for DRM when page is not 1, graph is 0, and ao is not 0', async () => {
    //     mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
    //     const response = await DynamicReleaseManagementService.getDynamicReleaseData({ graph: 0, ao: 1, page: 2, appliedFilters });
    //     expect(response.status).toBe(200);
    //     expect(mockedAxios.put).toHaveBeenCalledWith(
    //         'http://10.8.1.10:9000/getDynamicReleaseData/?graph=0&ao=1&page=2',
    //         appliedFilters,
    //         {
    //             headers: {
    //                 'Content-Type': 'application/json',
    //             }
    //         }
    //     );
    // });

    it('should handle an error when releasing the selected orders', async () => {
        mockedAxios.put.mockRejectedValueOnce(new Error('Failed to release orders'));
        await expect(DynamicReleaseManagementService.updateDynamicReleaseData(dummyReleaseData)).rejects.toThrow('Failed to release orders');
    });
});
