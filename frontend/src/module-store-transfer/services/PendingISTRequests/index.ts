import { useQuery } from '@tanstack/react-query'
import { PendingISTRequestsService } from './api'

export const QUERY_KEYS = {
  useGetListIST: ['PendingISTRequestsService.useGetListIST']
}

export const useGetListIST = () => {
  return useQuery(
    QUERY_KEYS.useGetListIST,
    async () => await PendingISTRequestsService.getList()
  )
}
