import {BTRService} from './api';
import axios,{AxiosStatic} from 'axios';
jest.mock('axios');
const mockedAxios=axios as jest.Mocked<AxiosStatic>;
describe('Testing the BTRService',  () => {
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
  
    it('should make a get request to the /GetBTRData', async () => {
      mockedAxios.post.mockResolvedValueOnce({data:'test',status:200});
   
      const response = await BTRService.getBTRData({});
      // expect(mockedAxios.post).toHaveBeenCalledWith( process.env.REACT_APP_VF_API_HOST+'/getBTRData',{},{
      //   headers: { 'Content-Type': 'application/json' }
      // })
      expect(response.status).toBe(200);
  
    });

    it('should make a get request to the /GetBTRDataCount', async () => {
      mockedAxios.post.mockResolvedValueOnce({data:'test',status:200});
   
      const response = await BTRService.getBTRDataCount({data:'test',status:200});
      // expect(mockedAxios.post).toHaveBeenCalledWith( process.env.REACT_APP_VF_API_HOST+'/getBTRData',{},{
      //   headers: { 'Content-Type': 'application/json' }
      // })
      expect(response.status).toBe(200);
  
    });

   
  });

