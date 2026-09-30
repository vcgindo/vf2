import {OpenExpeditingRequestsService} from './api';
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
  
    it('should make a Post request to the /GetOpenExpediteRequest', async () => {
      mockedAxios.post.mockResolvedValueOnce({data:'test',status:200});
      const response = await OpenExpeditingRequestsService.getOpenExpediteRequestData({});
      expect(response.status).toBe(200);
  
    });

    it('should make a Post request to the /AddRemarkForExpedite', async () => {
        mockedAxios.post.mockResolvedValueOnce({data:'test',status:200});
        const mockBody = {
           remark:'',
           skucode:'',
           whcode:''
        }
        const response = await OpenExpeditingRequestsService.addRemarkForExpedite(mockBody);
        expect(response.status).toBe(200);
    
      }); 

      it('should make a Post request to the /GetRemarkDetailsForExpedite', async () => {
        mockedAxios.post.mockResolvedValueOnce({data:'test',status:200});
        const mockBody = {
           skucode:'',
           whcode:''
        }
        const response = await OpenExpeditingRequestsService.getRemarkDetailsForExpedite(mockBody);
        expect(response.status).toBe(200);
    
      }); 


  });

