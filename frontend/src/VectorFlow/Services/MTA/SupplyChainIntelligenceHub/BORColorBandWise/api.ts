/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'
import { SubmitBORRemarkPayload } from '../../../../../VectorFlow/types/BPR';

export namespace BORColorBandWiseService {

    export const getBORColorBandWiseRecordCount = async (body:any) => {
        return axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetBOROrderAllocationReportDataCount`,body,{
            headers: { 'Content-Type': 'application/json' }
          })
      }

  
  export const getBORColorBandWisData = async(body:any)=>{
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetBOROrderAllocationReportData`,body,{
      headers:{ 'Content-Type': 'application/json' }
    })
  }

  export const submitBOROARemark = async (payload:{data:Array<SubmitBORRemarkPayload>}) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/AddBOROARemark`,{...payload,"forwardUsers":true},{
      headers:{ 'Content-Type': 'application/json' }
    });
  }

  export const getBOROARemarkHistory = async (payload:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetBOROARemarkDetails`,{...payload,"forwardUsers":true},{
      headers:{ 'Content-Type': 'application/json' }
    }); 
  }
}


