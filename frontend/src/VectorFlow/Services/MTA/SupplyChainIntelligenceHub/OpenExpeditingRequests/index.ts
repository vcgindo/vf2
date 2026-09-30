import { useMutation } from '@tanstack/react-query'

import { OpenExpeditingRequestsService } from './api'


export const QUERY_KEYS = {
    GetOpenExpediteRequestData: ['OpenExpeditingRequestsService.GetOpenExpediteRequestData'],
}


export const useGetOpenExpediteRequestData = () => {
    return useMutation(async (body:any) => {
      return await OpenExpeditingRequestsService.getOpenExpediteRequestData(body);
    });
  }

  export const useAddRemarkForExpedite = () => {
    return useMutation(async (body:any) => {
      return await OpenExpeditingRequestsService.addRemarkForExpedite(body);
    });
  }

  export const useGetRemarkDetailsForExpedite = () => {
    return useMutation(async (body:any) => {
      return await OpenExpeditingRequestsService.getRemarkDetailsForExpedite(body);
    });
  }
