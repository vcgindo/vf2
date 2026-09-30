import { useMutation } from '@tanstack/react-query'


import { OrderAllocationReportService } from './api'


export const QUERY_KEYS = {
//   useGetBPRUIConfiguration: ['BPRService.useGetBPRUIConfiguration'],
}



export const useGetOrderAllocationReportRecordsCount =()=>{
  return useMutation(async(body:any)=>{
    return await OrderAllocationReportService.getOrderAllocationReportRecordsCount(body)
  })
}

export const useGetOrderAllocationReportData =()=>{
    return useMutation(async(body:any)=>{
      return await OrderAllocationReportService.getOrderAllocationReportData(body)
    })
  }