import { useQuery,useMutation } from '@tanstack/react-query'
import { BORDataPayload, SubmitBORRemarkPayload } from '../../../../../VectorFlow/types/BPR';

import { SupplyChainIntelligenceHubService } from './api'


export const QUERY_KEYS = {
  useGetBORUIConfiguration: ['MDMService.useGetBORUIConfiguration'],
  useBORData:['MDMService.useBORData'],
  useBORDataCount:['MDMService.useBORDataCount'],
  useGetBORAnalyticsData:["BORService.useGetBORAnalyticsData"]
}


export const useGetBORUIConfiguration = () => {
    return useQuery(QUERY_KEYS.useGetBORUIConfiguration,async () => {
      return await SupplyChainIntelligenceHubService.getBORUIConfiguration();
    });
  }
  export const useBORData=()=>{
    return useMutation(async (body:any) => {
      return await SupplyChainIntelligenceHubService.getBORData(body);
    });
  }

 
  
  export const useBORDataCount = () => {
    return useMutation(async (body:any) => {
      return await SupplyChainIntelligenceHubService.getBORDataCount(body);
    });
  }

  export const useGetBORAnalyticsData = () => {
    return useQuery(QUERY_KEYS.useGetBORAnalyticsData,async () => {
      return await SupplyChainIntelligenceHubService.getBORAnalyticsData();
    });
  }

  export const useGetSubmitBORRemark = () => {
    return useMutation(async (payload:{data:Array<SubmitBORRemarkPayload>}) => {
      return await SupplyChainIntelligenceHubService.submitBORRemark(payload);
    });

    


    // export const useGetBORRemarkHistory = () => {
    //   return useMutation(async (payload:BORDataPayload) => {
    //     return await BORService.getRemarkHistory(payload);
    //   });
    // }

  }

  export const useGetBORRemarkHistory = () => {
    return useMutation(async (payload:BORDataPayload) => {
      return await SupplyChainIntelligenceHubService.getBORRemarkHistory(payload);
    });
  }

  export const useSubmitBORRemark = () => {
    return useMutation(async (payload:{data:Array<SubmitBORRemarkPayload>}) => {
      return await SupplyChainIntelligenceHubService.submitBORRemark(payload);
    });
  }
  