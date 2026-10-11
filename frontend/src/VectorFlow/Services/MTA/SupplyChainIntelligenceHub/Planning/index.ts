import { useMutation } from '@tanstack/react-query'
import { PlanningService } from './api'


export const QUERY_KEYS = {
    useGetPlanningDataCount: ['MDMService.useGetPlanningDataCount'],
    useGetPlanningData: ['MDMService.useGetPlanningData'],

 
}

export const useGetPlanningDataCount = ()=>{
    return useMutation(async(body:any)=>{
      return await PlanningService.getPlanningDataCount(body);
    })
  }

export const useGetPlanningDataGraph = ()=>{
    return useMutation(async(body:any)=>{
        return await PlanningService.getPlanningDataGraph(body);
    })
}

export const useGetPlanningDataGrid = ()=>{
  return useMutation(async(body:any)=>{
      return await PlanningService.getPlanningDataGrid(body);
  })
}

export const useGetPlanningDataCustom = ()=>{
  return useMutation(async(body:any)=>{
      return await PlanningService.getPlanningDataCustom(body);
  })
}

export const useSubmitOpenExpediteRequest = ()=>{
  return useMutation(async(body:any)=>{
    return await PlanningService.submitOpenExpediteRequest(body);
})
}

export const useGetPlanningDataGridCount =()=>{
  return useMutation(async(body:any)=>{
    return await PlanningService.getPlanningDataGridCount(body)
  })
}


