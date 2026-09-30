/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'


export namespace OpenExpeditingRequestsService {

  export const getOpenExpediteRequestData = async (body:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetOpenExpediteRequest`,body,{
      headers:{ 'Content-Type': 'application/json' }
    });
  }
  
  export const addRemarkForExpedite = async (body:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/AddRemarkForExpedite`,{...body, "forwardUsers":true},{
      headers:{ 'Content-Type': 'application/json' }
    });
  }

  export const getRemarkDetailsForExpedite = async (body:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetRemarkDetailsForExpedite`,{...body, "forwardUsers":true},{
      headers:{ 'Content-Type': 'application/json' }
    });
  }
}

