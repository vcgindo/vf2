/* eslint-disable @typescript-eslint/no-namespace */
import axios from "axios";

import {RRRDataPayload} from '../../../../types/RRR'
import {SubmitDueDatePayload} from "../../../../types/BPR";
export namespace EOServices {

    export const getEOUIConfiguration = async () => {
        return await axios.get(process.env.REACT_APP_API_HOST+ `api/mta/EOUIConfig`);
      }
    
    export const getEOData = async (body:RRRDataPayload) => {
      return await axios.post(process.env.REACT_APP_API_HOST+ `api/mta/GetElephantOrderData`,body,{
        headers:{ 'Content-Type': 'application/json' }
      });
    }

    export const getEODataCount = async (body:RRRDataPayload) => {
      return await axios.post(process.env.REACT_APP_API_HOST+ `api/mta/GetElephantOrderDataCount`,body,{
        headers:{ 'Content-Type': 'application/json' }
      });
    }

    export const submitDueDates = async (payload:{data:Array<SubmitDueDatePayload>}) => {
      return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/UpdateElephantOrderDueDates`,{"forwardUsers":false, ...payload},{
        headers:{ 'Content-Type': 'application/json' }
      });
    }  
}