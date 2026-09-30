import {useMutation } from '@tanstack/react-query'


import { BTRService } from './api'


export const QUERY_KEYS = {
  useGetBTRDataCount:['useGetBTRDataCount']
}

export const useGetBTRDataCount = () => {
  return useMutation(async (body:any) => {
    return await BTRService.getBTRDataCount(body)
  });
}


export const useGetBTRData = () => {
    return useMutation(async (body:any) => {
      return await BTRService.getBTRData(body)
    });
  }

  