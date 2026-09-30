/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'
import { SubmitBORRemarkPayload } from '../../../../../VectorFlow/types/BPR';


export namespace SupplyChainIntelligenceHubService {

  export const getBORUIConfiguration = async () => {
    return await axios.get(process.env.REACT_APP_API_HOST +`api/mta/BORUIConfig`);
  }

  // export const getBORData = async (body:{filters:Array<{attributeName:string,op:string,value:string}>,paginationParameter:{pageNumber:number,recordsPerPage:number}}) => {
  //   return await axios.post(process.env.REACT_APP_API_HOST +`/BORData`,body,{
  //     headers: { 'Content-Type': 'application/json' }
  //   });
  // }

  export const getBORData = async (body:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST +`api/mta/BORData`, body, {
      headers: { 'Content-Type': 'application/json' }
    });
}


   export const getBORDataCount = async ( body:{filters:any,paginationParameter:{pageNumber:number,recordsPerPage:number}}) => {
    return await axios.post(process.env.REACT_APP_API_HOST +`api/mta/BORDataCount`, body,{
      headers: { 'Content-Type': 'application/json' }
    });
  }

  export const getBORAnalyticsData = async () => {
    return await axios.get(process.env.REACT_APP_API_HOST +`api/mta/BORAnalytics`,{
      headers: { 'Content-Type': 'application/json' }
    });
  }

  export const submitBORRemark = async (payload:{data:Array<SubmitBORRemarkPayload>}) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/AddBORRemark`,{...payload,"forwardUsers":true},{
      headers:{ 'Content-Type': 'application/json' }
    });
  }

  export const getBORRemarkHistory = async (payload:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetBORRemarkDetails`,{...payload,"forwardUsers":true},{
      headers:{ 'Content-Type': 'application/json' }
    }); 
  }
}

