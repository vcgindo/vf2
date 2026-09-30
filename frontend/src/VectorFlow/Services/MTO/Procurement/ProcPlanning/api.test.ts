import axios, { AxiosStatic } from 'axios';
import { ProcPlanningService } from './api';

jest.mock('axios');

const mockedAxios = axios as jest.Mocked<AxiosStatic>;

describe('ProcPlanningService', () => {
    const mockDate = '2024-06-01';
    const pageNum = '1';
    const mockResponse = {
        data: {
            results: [
                { id: 1, name: 'Item 1' },
                { id: 2, name: 'Item 2' }
            ]
        }
    };

    beforeEach(() => {
        jest.spyOn(axios, 'get').mockResolvedValueOnce(mockResponse);
        jest.spyOn(axios, 'patch').mockResolvedValueOnce(mockResponse);
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    it('should fetch procurement planning data correctly', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        
        const response = await ProcPlanningService.GetProcPlanningData(mockDate, pageNum, '1', {});

        // expect(axios.put).toHaveBeenCalledWith(`${process.env.REACT_APP_VF_API_HOST_MTO}/getProcPlanningData/?releaseDate=${mockDate}&page=${pageNum}&ca=1&page_size=500`, 
        // {},
        // {
        //     headers: { 'Content-Type': 'application/json' }
        // });

        expect(response.status).toBe(200);
        // expect(response).toEqual(mockResponse);
    });
    it('should fetch procurement planning data correctly with ca =0', async () => {
        mockedAxios.put.mockResolvedValueOnce({ data: 'test', status: 200 });
        
        const response = await ProcPlanningService.GetProcPlanningData(mockDate, pageNum, '0', {});

        // expect(axios.put).toHaveBeenCalledWith(`${process.env.REACT_APP_VF_API_HOST_MTO}/getProcPlanningData/?releaseDate=${mockDate}&page=${pageNum}&ca=0&page_size=500`, 
        // {},
        // {
        //     headers: { 'Content-Type': 'application/json' }
        // });
        expect(response.status).toBe(200);

        // expect(response).toEqual(mockResponse);
    });

    it('should fetch procurement data after simulation correctly', async () => {
        const response = await ProcPlanningService.GetProcDataAfterSimulation(mockDate, '0', '1');

        expect(axios.get).toHaveBeenCalledWith(`${process.env.REACT_APP_VF_API_HOST_MTO}/getProdDataAfterSimulation/?releaseDate=${mockDate}&eas=0&page=1&page_size=500`, {
            headers: { 'Content-Type': 'application/json' }
        });

        expect(response).toEqual(mockResponse);
    });

    it('should update batchwise component allocation at simulation correctly', async () => {
        const requestBody = [
            { sno: '1', on: 'ON-001', lid: '1', item: 'Item 1', easa: 100 },
            { sno: '2', on: 'ON-002', lid: '2', item: 'Item 2', easa: 200 }
        ];

        const response = await ProcPlanningService.UpdateBatchWiseCompAllSimulation(requestBody);

        expect(axios.patch).toHaveBeenCalledWith(`${process.env.REACT_APP_VF_API_HOST_MTO}/updateBatchwiseCompAllocAtSimulation/`, JSON.stringify(requestBody), {
            headers: { 'Content-Type': 'application/json' }
        });

        expect(response).toEqual(mockResponse);
    });


    it('should update order due date', async () => {
        const requestBody = {
            "username": "user2",
            "stock": [
                {
                    "ic": "RM1",
                    "as": 100
                },
                {
                    "ic": "RM2",
                    "as": 51
                },
                {
                    "ic": "RM3",
                    "as": 300
                }
            ]
        }

        mockedAxios.post.mockResolvedValueOnce({ data: 'test', status: 200 });
        const response = await ProcPlanningService.UpdateProcurementSimulationData(requestBody);
        expect(response.status).toBe(200);
    });


});
