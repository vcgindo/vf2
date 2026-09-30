import { useQuery,useMutation } from '@tanstack/react-query'

import { EOServices } from './api'
import {RRRDataPayload} from '../../../../types/RRR'
import {SubmitDueDatePayload} from "../../../../types/BPR";


export const QUERY_KEYS = {
  useGetEOUIConfiguration: ['EOServices.getEOUIConfiguration'],
  useGetEOData : ['EOServices.getEOData'],
  useGetEODataCount: ['EOServices.getEODataCount']
}


export const useGetEOUIConfiguration =  () => {
    return useQuery(QUERY_KEYS.useGetEOUIConfiguration,async () => {
      return await EOServices.getEOUIConfiguration();
    });
  }

export const useGetEOData  = ()=>{
  return useMutation(QUERY_KEYS.useGetEOData,async (body:RRRDataPayload)=>{
    return await EOServices.getEOData(body);
  })
}

export const useGetEODataCount  = ()=>{
  return useMutation(QUERY_KEYS.useGetEODataCount,async (body:RRRDataPayload)=>{
    return await EOServices.getEODataCount(body);
  })
}

export const useSubmitDueDates = () => {
  return useMutation(async (payload: { data: Array<SubmitDueDatePayload> }) => {
    return await EOServices.submitDueDates(payload);
  });
};
