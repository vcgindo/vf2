import { useQuery,useMutation } from '@tanstack/react-query'

import { SDRServices } from './api'
import {RRRDataPayload} from '../../../../types/RRR'


export const QUERY_KEYS = {
  useGetSDRUIConfiguration: ['SDRServices.getSDRUIConfiguration'],
  useGetSDRData : ['SDRServices.getSDRData'],
  useGetSDRDataCount: ['SDRServices.getSDRDataCount']
}


export const useGetSDRUIConfiguration =  () => {
    return useQuery(QUERY_KEYS.useGetSDRUIConfiguration,async () => {
      return await SDRServices.getSDRUIConfiguration();
    });
  }

export const useGetSDRData  = ()=>{
  return useMutation(QUERY_KEYS.useGetSDRData,async (body:RRRDataPayload)=>{
    return await SDRServices.getSDRData(body);
  })
}

export const useGetSDRDataCount  = ()=>{
  return useMutation(QUERY_KEYS.useGetSDRDataCount,async (body:RRRDataPayload)=>{
    return await SDRServices.getSDRDataCount(body);
  })
}

