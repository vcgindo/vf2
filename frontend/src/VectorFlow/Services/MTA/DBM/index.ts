import { useQuery,useMutation } from '@tanstack/react-query'
import { DBMServices } from './api'

export const QUERY_KEYS = {
  useGetDBMUIConfiguration: ['DBMServices.useGetDBMUIConfiguration'],
  useGetDBMData : ['DBMServices.getDBMData'],
  useGetDBMDataCount: ['DBMServices.getDBMDataCount'],
  useGetDBMApplySelectedNorm: ['DBMServices.getDBMApplySelectedNorm'],
  useGetDBMUpdateSleepTbl: ['DBMServices.getDBMUpdateSleepTbl'],
  useGetDBMAnalyticsData:['DBMService.useGetDBMAnalyticsData']
}


export const useGetDBMUIConfiguration =  () => {
    return useQuery(QUERY_KEYS.useGetDBMUIConfiguration,async () => {
      return await DBMServices.getDBMUIConfig();
    });
  }
  export const useGetDBMData=()=>{
    return useMutation(async (body:{filters:any,paginationParameter:{pageNumber:number,recordsPerPage:number}}) => {
      return await DBMServices.getDBMData(body);
    });
  }
  export const useGetDBMDataCount  = ()=>{
    return useMutation(QUERY_KEYS.useGetDBMDataCount,async (body:{filters:any,paginationParameter:{pageNumber:number,recordsPerPage:number}})=>{
      return await DBMServices.getDBMDataCount(body);
    })
  }
  export const useGetDBMApplySelectedNorm  = ()=>{
    return useMutation(QUERY_KEYS.useGetDBMApplySelectedNorm,async (body:{data:Array<{SKUCode:string,LocCode:string}>,paginationParameter:{pageNumber:number,recordsPerPage:number},filters:any})=>{
      return await DBMServices.getDBMApplySelectedNorm(body);
    })
  }
  // export const useGetDBMUpdateSleepTbl  = ()=>{
  //   return useMutation(QUERY_KEYS.useGetDBMUpdateSleepTbl,async (body:{data:Array<{SKUCode:string,LocCode:string}>,paginationParameter:{pageNumber:number,recordsPerPage:number},filters:Array<{attributeName:string,op:string,value:string}>})=>{
  //     return await DBMServices.getDBMUpdateSleepTbl(body);
  //   })
  // }

  export const useGetDBMUpdateSleepTbl  = ()=>{
    return useMutation(QUERY_KEYS.useGetDBMUpdateSleepTbl,async (body:{data:Array<{SKUCode:string,WHCode:string}>})=>{
      return await DBMServices.getDBMUpdateSleepTbl(body);
    })
  }

  export const useGetDBMAnalyticsData  = ()=>{
    return useQuery(QUERY_KEYS.useGetDBMAnalyticsData,async ()=>{
      return await DBMServices.getDBMAnalyticsData();
    })
  }
