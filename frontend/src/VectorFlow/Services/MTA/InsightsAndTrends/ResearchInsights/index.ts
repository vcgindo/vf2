import { useMutation,useQuery } from '@tanstack/react-query'
import { ResearchInsightsService } from './api'


export const QUERY_KEYS = {
    useGetHistroricalAvailabilityData:['ResearchInsightsService.useGetHistroricalAvailabilityData']
}


export const useGetUpdatedGraphData = ()=>{
    return useMutation(async(body:any)=>{
        return await ResearchInsightsService.getUpdatedGraphData(body);
    })
}

export  const useGetHistroricalAvailabilityData = ()=>{
    return useQuery(QUERY_KEYS.useGetHistroricalAvailabilityData,async()=>{
        return await ResearchInsightsService.getHistoricalAvailabilityData()
      })
}
