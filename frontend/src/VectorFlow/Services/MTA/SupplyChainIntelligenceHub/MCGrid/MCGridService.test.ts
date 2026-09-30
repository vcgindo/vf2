import { MCGridService } from './api';


jest.mock('axios');


describe('Testing the MDMService',  () => {
    const OLD_ENV = process.env;
    beforeEach(() => {
      jest.resetModules() // Most important - it clears the cache
      process.env = { ...OLD_ENV }; // Make a copy
    });
  
    process.env.REACT_APP_VF_API_HOST = 'http://10.8.1.10:8082';
    process.env.REACT_APP_VF_MOCK_API_HOST = 'http://10.8.1.10:8081'
  
    afterEach(() => {
      jest.clearAllMocks();
    });
  

    it('should make a Post request to api/ist/supply-chain-intelligence-hub/health-of-grid', async () => {
        const mockBody:any = {
        }
        await MCGridService.getGridHealth(mockBody);
      });


  });