/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'



export namespace InTransitWhereAboutsService {

export const getInTransitWhereAboutsDataCount = async (body:any) => {
  return await axios.post(process.env.REACT_APP_API_HOST + `/api/mta/GetInTransitWhereAboutsDataCount`,body,{
      headers:{ 'Content-Type': 'application/json' }
    });
}

  export const getInTransitWhereAboutsData = async (body:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `/api/mta/GetInTransitWhereAboutsData`,body,{
        headers:{ 'Content-Type': 'application/json' }
      });
  }

  export const getRemarkDetailsForInTransit = async (body:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `/api/mta/GetRemarkDetailsForInTransit`,{...body,"forwardUsers":true},{
        headers:{ 'Content-Type': 'application/json' }
      });
  }

  export const submitRemarksForInTransit = async (body:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `/api/mta/SubmitRemarksForInTransit`,{...body,"forwardUsers":true},{
        headers:{ 'Content-Type': 'application/json' }
      });
  }

  export const getTransporterDetails = async (body:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `/api/mta/GetTransporterDetails`,body,{
        headers:{ 'Content-Type': 'application/json' }
      });
  }

}

