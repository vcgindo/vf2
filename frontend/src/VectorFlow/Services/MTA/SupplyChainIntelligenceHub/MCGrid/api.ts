/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'


export namespace MCGridService {

  export const getGridHealth = async (payload:any) => {
    return await axios.post(`${process.env.REACT_APP_VF_MOCK_API_HOST }/api/ist/supply-chain-intelligence-hub/health-of-grid`,payload,{
      headers:{ 'Content-Type': 'application/json' }
    });
  }

}


