import { useMutation, useQuery } from '@tanstack/react-query'
import { ISTService } from './api'
import { type ChangeType } from './../../types/ist'

export const QUERY_KEYS = {
  useGetLocation: ['MainService.useGetLocation'],
  UseGetPendingFilter: ['MainService.UseGetPendingFilter'],
  UseGetReceiverFilter: ['MainService.UseReceiverFilter']
}

export const useGetLocationFilter = (url: string) => {
  return useQuery(QUERY_KEYS.useGetLocation, async () => {
    return await ISTService.getLocationFilter(url)
  })
}

export const UseGetPendingFilter = (data: any) => {
  return useQuery(QUERY_KEYS.UseGetPendingFilter, async () => {
    return await ISTService.getPendingFilter(data)
  })
}

export const UsePutItemCodeChangeTye = () => {
  return useMutation(async (payload: ChangeType) => {
    return await ISTService.putItemCodeChangeType(payload)
  })
}

export const UseGetReceiverFilter = (url: string) => {
  return useQuery(QUERY_KEYS.UseGetReceiverFilter, async () => {
    return await ISTService.getReceiverFilter(url)
  })
}
