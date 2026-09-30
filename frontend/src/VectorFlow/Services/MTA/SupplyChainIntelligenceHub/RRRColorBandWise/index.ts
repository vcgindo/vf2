import { useMutation } from '@tanstack/react-query'


import { RRRColorBandWiseService } from './api'


export const QUERY_KEYS = {
//   useGetBPRUIConfiguration: ['BPRService.useGetBPRUIConfiguration'],
}



export const useGetRRRColorBandWiseRecordCount =()=>{
  return useMutation(async(body:any)=>{
    return await RRRColorBandWiseService.getRRRColorBandWiseRecordCount(body)
  })
}

export const useGetRRRColorBandWiseData =()=>{
    return useMutation(async(body:any)=>{
      return await RRRColorBandWiseService.getRRRColorBandWiseData(body)
    })
  }