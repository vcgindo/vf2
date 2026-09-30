import { useMutation } from '@tanstack/react-query'
import { MaterialCoverageServices } from './api'

//useQuery for get 
export const QUERY_KEYS = {
    useGetSummarySo: ['MDMService.useGetSummarySO'],
    useGetOpenSODetailsData:['MDMService.useGetOpenSODetailsData']
}

export const useGetSOSummaydetails = ()=>{
    // return useMutation(async(params: {appliedFilters: any})=>{
    //   return await MaterialCoverageServices.getMaterialSOData(params)
    // })
  
    return useMutation(async()=>{
      return await MaterialCoverageServices.getMaterialSOData()
    })
  }

export const useGetOpenSODetailsData = () => {
  return useMutation(async(data:any)=>{
        return MaterialCoverageServices.getOpenSODetailsData(data)
    })
}

export const useGetOpenSODetailsDataForExcelExport = () =>{
  return useMutation(async(data:any)=>{
        return MaterialCoverageServices.getOpenSODetailsDataForExcelExport(data)
    })
}
