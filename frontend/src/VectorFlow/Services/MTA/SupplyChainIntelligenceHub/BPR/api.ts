/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'
import { AnalyticsDataPayload, BPRDataPayload, SubmitBPRRemarkPayload } from '../../../../../VectorFlow/types/BPR';


export namespace BPRService {

  export const getBPRUIConfiguration = async () => {
    return await axios.get(process.env.REACT_APP_API_HOST + `api/mta/GetBPRUIConfig`,{
      headers:{ 'Content-Type': 'application/json' }
    });
  }
  
  
  export const getBPRDataCount = async (payload:BPRDataPayload) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetBPRDataCount`,payload,{
      headers:{ 'Content-Type': 'application/json' }
    });
  }

  export const getBPRData = async (payload:BPRDataPayload) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetBPRData`,payload,{
      headers:{ 'Content-Type': 'application/json' }
    });
  }

  export const submitRemark = async (payload:{data:Array<SubmitBPRRemarkPayload>}) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/AddRemark`,{...payload,"forwardUsers":true},{
      headers:{ 'Content-Type': 'application/json' }
    });
  }

  export const getRemarkHistory = async (payload:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetRemarkDetails`,{...payload,"forwardUsers":true},{
      headers:{ 'Content-Type': 'application/json' }
    }); 
  }

  export const getAllSKUs=async()=>{
    // return await axios.get(`https://requestly.tech/api/mockv2/GetAllSKU?username=user1708583815102&`,{
      return await axios.get(process.env.REACT_APP_API_HOST + 'api/mta/SKUDesc',{
      headers:{ 'Content-Type': 'application/json' }
    });
  }

  export const getAllLocations=async()=>{
    // return await axios.get(`https://requestly.tech/api/mockv2/GetAllSKU?username=user1708583815102&`,{
      return await axios.get(process.env.REACT_APP_API_HOST + `api/mta/WHDesc`,{
      headers:{ 'Content-Type': 'application/json' }
    });
  }

  export const getDailyData = async (payload:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/DailyDataGraph`,payload,{
      headers:{ 'Content-Type': 'application/json' }
    }); 
  }

  export const saveState = async (payload:{reportname:string,state:string}) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/SaveState`,payload,{
      headers:{ 'Content-Type': 'application/json' }
    }); 
  }

  export const getState = async (payload:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetState`,payload,{
      headers:{ 'Content-Type': 'application/json' }
    }); 
  }

  export const resetState = async (payload:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/ResetState`,payload,{
      headers:{ 'Content-Type': 'application/json' }
    }); 
  }

  export const getAnalyticsData = async (payload:AnalyticsDataPayload) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetAnalyticsData`,payload,{
      headers:{ 'Content-Type': 'application/json' }
    }); 
  }

  export const getInTransitWhereAboutAnalytics = async()=>{
    return await axios.get(process.env.REACT_APP_API_HOST + 'api/mta/GetInTransitWhereAboutAnalytics',{
      headers:{ 'Content-Type': 'application/json' }
    })
  }

  export const getOpenExpediteAnalytics = async()=>{
    return await axios.get(process.env.REACT_APP_API_HOST + 'api/mta/OpenExpediteAnalytics',{
      headers:{ 'Content-Type': 'application/json' }
    })
  }

  export const getLocationTypes = async()=>{
    return await axios.get(process.env.REACT_APP_API_HOST + 'api/mta/LocationType',{
      headers:{ 'Content-Type': 'application/json' }
    })
  }

  export const getlastRunDate = async()=>{
    return await axios.get(process.env.REACT_APP_API_HOST + 'api/mta/GetLastRunDate',{
      headers:{ 'Content-Type': 'application/json' }
    })
  }

  export const getUiConfig = async(reportName:string)=>{
    return await axios.get(process.env.REACT_APP_API_HOST + `api/mta/GetUIConfig?reportName=${reportName}`,{
      headers:{ 'Content-Type': 'application/json' }
    })
  }
}

export const getBPRDataForExcelDownload = async (payload:BPRDataPayload) => {
  return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetBPRData`,payload,{
    headers:{ 'Content-Type': 'application/json' }
  });
}


