/* eslint-disable @typescript-eslint/no-namespace */
import axios from "axios";

export namespace DBMServices {
    
    export const getDBMUIConfig = async () => {
        return await axios.get(process.env.REACT_APP_API_HOST+ `api/mta/DBMUIConfig`);
      }
    
      export const getDBMData = async (body:{filters:Array<{attributeName:string,op:string,value:string}>,paginationParameter:{pageNumber:number,recordsPerPage:number}}) => {
        return await axios.post(process.env.REACT_APP_API_HOST +`api/mta/DBMData`,body,{
          headers: { 'Content-Type': 'application/json' }
        });
      }

      export const getDBMDataCount = async (body:{filters:Array<{attributeName:string,op:string,value:string}>,paginationParameter:{pageNumber:number,recordsPerPage:number}}) => {
        return await axios.post(process.env.REACT_APP_API_HOST+ `api/mta/DBMDataCount`,body,{
          headers:{ 'Content-Type': 'application/json' }
        });
      }

      export const getDBMApplySelectedNorm = async (body:{data:Array<{SKUCode:string,LocCode:string}>,paginationParameter:{pageNumber:number,recordsPerPage:number},filters:Array<{attributeName:string,op:string,value:string}>}) => {
        return await axios.post(process.env.REACT_APP_API_HOST+ `api/mta/DBMApplySelectedNorms`,body,{
          headers:{ 'Content-Type': 'application/json' }
        });
      }

      // export const getDBMUpdateSleepTbl = async (body:{data:Array<{SKUCode:string,LocCode:string}>,paginationParameter:{pageNumber:number,recordsPerPage:number},filters:Array<{attributeName:string,op:string,value:string}>}) => {
      //   return await axios.post(process.env.REACT_APP_API_HOST+ `/DBMUpdateSleepTbl`,body,{
      //     headers:{ 'Content-Type': 'application/json' }
      //   });
      // }

      export const getDBMUpdateSleepTbl = async (body:{data: Array<{SKUCode:string,WHCode:string}>}) => {
        return await axios.post(process.env.REACT_APP_API_HOST+ `api/mta/DBMUpdateSleepTbl`,body,{
          headers:{ 'Content-Type': 'application/json' }
        });
      }

      export const getDBMAnalyticsData = async () => {
        return await axios.get(process.env.REACT_APP_API_HOST+ `api/mta/DBMAnalytics`,{
          headers:{ 'Content-Type': 'application/json' }
        });
      }
}