import { useQuery,useMutation } from '@tanstack/react-query'

import { RRRServices } from './api'
import {RRRDataPayload} from '../../../../types/RRR'


export const QUERY_KEYS = {
  useGetRRRUIConfiguration: ['RRRServices.useGetRRRUIConfiguration'],
  useGetRRRData : ['RRRServices.getRRRData'],
  useGetRRRDataCount: ['RRRServices.getRRRDataCount'],
  useGetRRRAnalyticsData:['RRRServices.useGetRRRAnalyticsData']
}


export const useGetRRRUIConfiguration =  () => {
    return useQuery(QUERY_KEYS.useGetRRRUIConfiguration,async () => {
      return await RRRServices.getRRRUIConfiguration();
    });
  }

export const useGetRRRData  = ()=>{
  return useMutation(QUERY_KEYS.useGetRRRData,async (body:RRRDataPayload)=>{
    return await RRRServices.getRRRData(body);
  })
}

export const useGetRRRDataCount  = ()=>{
  return useMutation(QUERY_KEYS.useGetRRRDataCount,async (body:RRRDataPayload)=>{
    return await RRRServices.getRRRDataCount(body);
  })
}

export const useGetRRRAnalyticsData  = ()=>{
  return useQuery(QUERY_KEYS.useGetRRRAnalyticsData,async ()=>{
    return await RRRServices.getRRRAnalyticsData();
  })
}

