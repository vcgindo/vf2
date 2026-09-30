import {InsightsAndTrendsService} from './api';
import { useMutation } from '@tanstack/react-query'
export const QUERY_KEYS = {
  useGetAvailabilityTrend: ['InsightsAndTrendsService.useGetAvailabilityTrend'],
useGetChronicUnavailabilityLoc:['InsightsAndTrendsService.useGetChronicUnavailabilityLoc'],
useGetChronicUnavailabilitySku:['InsightsAndTrendsService.useGetChronicUnavailabilitySku'],
useGetAvailabilityAgeing:['InsightsAndTrendsService.useGetAvailabilityAgeing'],
useGetDBMNormSuggestionLoc:['InsightsAndTrendsService.useGetDBMNormSuggestionLoc'],
useGetDBMNormSuggestionPie:['InsightsAndTrendsService.useGetDBMNormSuggestionPie'],
useGetDBMNormSuggestionSKUs:['InsightsAndTrendsService.useGetDBMNormSuggestionSKUs'],
useGetDBMNormSuggestionAgeing:['InsightsAndTrendsService.useGetDBMNormSuggestionAgeing'],
useGetExcessInventorySku:['InsightsAndTrendsService.useGetExcessInventorySku'],
useGetExcessInventoryValue:['InsightsAndTrendsService.useGetExcessInventoryValue'],
useGetChronicUnavailabilityGridView:['InsightsAndTrendsService.useGetChronicUnavailabilityGridView']
}
export const useGetAvailabilityTrend = ()=>{
  return useMutation(async (body:{horison:number})=>{
    return await InsightsAndTrendsService.getAvaialabilityTrend(body)
  })
}
export const useGetChronicUnavailabilityLoc = ()=>{
  return useMutation(async()=>{
    return await InsightsAndTrendsService.getChronicUnavailabilityLoc()
  })
}
export const useGetChronicUnavailabilitySku = ()=>{
  return useMutation(async()=>{
    return await InsightsAndTrendsService.getChronicUnavailabilitySku()
  })
}
// export const useGetAvailabilityAgeing = (horizon:number)=>{
//   return useMutation(QUERY_KEYS.useGetAvailabilityAgeing,async()=>{
//     return await InsightsAndTrendsService.getAvailabilityAgeing(horizon)
//   })
// }
export const useGetAvailabilityAgeing = () => {
    return useMutation(async (body:{horison:number,ageing:number}) => {
      return await InsightsAndTrendsService.getAvailabilityAgeing(body);
    });
  }

export const useGetDBMNormSuggestionLoc= ()=>{
  return useMutation(async()=>{
    return await InsightsAndTrendsService.getDBMNormSuggestionLoc()
  })
}
export const useGetDBMNormSuggestionPie= ()=>{
  return useMutation(async()=>{
    return await InsightsAndTrendsService.getDBMNormSuggestionPie()
  })
}
export const useGetDBMNormSuggestionSKUs = ()=>{
  return useMutation(async()=>{
    return await InsightsAndTrendsService.getDBMNormSuggestionSKUs()
  })
}
export const useGetDBMNormSuggestionAgeing = ()=>{
  return useMutation(async()=>{
    return await InsightsAndTrendsService.getDBMNormSuggestionAgeing()
  })
}
export const useGetExcessInventorySku = ()=>{
  return useMutation(async(body:{horison:number})=>{
    return await InsightsAndTrendsService.getExcessInventorySku(body)
  })
}
export const useGetExcessInventoryValue = ()=>{
  return useMutation(async(body:{horison:number})=>{
    return await InsightsAndTrendsService.getExcessInventoryValue(body)
  })

}

  export const useGetChronicUnavailabilityGridView = ()=>{
  return useMutation(async(body:any)=>{
    return await InsightsAndTrendsService.getChronicUnavailabilityGridView(body)
  })}