import { useMutation, useQueryClient } from '@tanstack/react-query'
import cloneDeep from 'lodash/cloneDeep'
import { MainService } from '../../../../../module-main/services/api'
import { PlanningService } from './api'


export const QUERY_KEYS = {
    useGetPlanningDataCount: ['MDMService.useGetPlanningDataCount'],
    useGetPlanningData: ['MDMService.useGetPlanningData'],

 
}

export const useGetPlanningDataCount = ()=>{
    const queryClient = useQueryClient();
    return useMutation(async(body:any)=>{
      const auth = JSON.stringify(await MainService.acquireToken());
      // Validate current access and generation before consulting retained data.
      const identityReply = await PlanningService.getSummaryIdentity(body);
      const identity = identityReply.data?.data?.identity;
      const businessDate = identityReply.data?.data?.businessDate;
      if (typeof identity !== 'string' || !identity) throw new Error('Planning identity unavailable');
      if (typeof businessDate !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(businessDate)) throw new Error('Planning summary date unavailable');
      const result = await queryClient.fetchQuery({
        queryKey: ['planning-summary', identity],
        staleTime: Infinity,
        cacheTime: 5 * 60 * 1000,
        retry: false,
        queryFn: async () => {
          const response = await PlanningService.getPlanningDataCount({ ...body, _report_read_identity: identity });
          if (response.status !== 200 || response.data?.status !== 200) throw new Error('Planning summary unavailable');
          return { ...response, config: {} as typeof response.config, data: cloneDeep(response.data) };
        }
      });
      if (auth !== JSON.stringify(await MainService.acquireToken())) {
        queryClient.removeQueries({ queryKey: ['planning-summary'] });
        throw new Error('Authentication changed during Planning read');
      }
      return { ...result, data: cloneDeep(result.data),
        headers: { ...result.headers, 'x-planning-business-date': businessDate } };
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


