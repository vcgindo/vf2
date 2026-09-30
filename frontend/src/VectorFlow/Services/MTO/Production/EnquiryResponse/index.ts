import { useQuery } from '@tanstack/react-query'
import { EnquiryResponseService } from './api'

export const QUERY_KEYS = {
    useGetEnquiryresponseData: ['MDMService.useGetEnquiryresponseData'],
}

export const useGetEnquiryResData = ()=>{
    return useQuery(QUERY_KEYS.useGetEnquiryresponseData,async()=>{
      return await EnquiryResponseService.getEnquiryData()
    })
  }
