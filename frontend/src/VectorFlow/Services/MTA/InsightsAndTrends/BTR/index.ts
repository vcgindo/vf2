import {useMutation } from '@tanstack/react-query'


import { BTRService } from './api'


export const QUERY_KEYS = {
  useGetBTRDataCount:['useGetBTRDataCount']
}

export const useGetBTRDataCount = () => {
  return useMutation(async (body:any) => {
    const { signal, ...payload } = body;
    return await BTRService.getBTRDataCount(payload, signal)
  });
}


export const useGetBTRData = () => {
    return useMutation(async (body:any) => {
      const { signal, ...payload } = body;
      return await BTRService.getBTRData(payload, signal)
    });
  }
