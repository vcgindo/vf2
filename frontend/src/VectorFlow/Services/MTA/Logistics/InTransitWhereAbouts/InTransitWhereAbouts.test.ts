import {InTransitWhereAboutsService} from './api';
import axios,{AxiosStatic} from 'axios';
jest.mock('axios');
const mockedAxios=axios as jest.Mocked<AxiosStatic>;
describe('Testing the BORService',  () => {
    const OLD_ENV = process.env;
    beforeEach(() => {
      jest.resetModules() // Most important - it clears the cache
      process.env = { ...OLD_ENV }; // Make a copy
    });
  process.env.REACT_APP_VF_API_HOST ='http://10.8.1.10:8082';
  //  process.env.REACT_APP_VF_API_HOST = 'http://10.8.1.10:8888';
  
    afterEach(() => {
      jest.clearAllMocks();
    });
  
    it('should make a Post request to the /api/SCIH/GetInTransitWhereAboutsDataCount', async () => {
      mockedAxios.post.mockResolvedValueOnce({data:'test',status:200});
      const response = await InTransitWhereAboutsService.getInTransitWhereAboutsDataCount({});
      expect(response.status).toBe(200);
  
    });

    it('should make a Post request to the /api/SCIH/GetInTransitWhereAboutsData', async () => {
        mockedAxios.post.mockResolvedValueOnce({data:'test',status:200});
        const response = await InTransitWhereAboutsService.getInTransitWhereAboutsData({
            pageNumber:1,
            recordsPerPage:100
          });
        expect(response.status).toBe(200);
    
      }); 

      it('should make a Post request to the /api/SCIH/GetRemarkDetailsForInTransit', async () => {
        mockedAxios.post.mockResolvedValueOnce({data:'test',status:200});
        const response = await InTransitWhereAboutsService.getRemarkDetailsForInTransit({});
        expect(response.status).toBe(200);
    
      }); 

      it('should make a Post request to the /api/SCIH/SubmitRemarksForInTransit', async () => {
        mockedAxios.post.mockResolvedValueOnce({data:'test',status:200});
        const response = await InTransitWhereAboutsService.submitRemarksForInTransit({});
        expect(response.status).toBe(200);
    
      }); 

      it('should make a Post request to the /api/SCIH/GetTransporterDetails', async () => {
        mockedAxios.post.mockResolvedValueOnce({data:'test',status:200});
        const response = await InTransitWhereAboutsService.getTransporterDetails({});
        expect(response.status).toBe(200);
    
      }); 


  });

