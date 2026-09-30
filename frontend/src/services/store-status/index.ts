import { useMutation, useQuery } from '@tanstack/react-query'
import { MainStore } from './api'
import { type ChangeStore } from './../../types/store'

export const QUERY_KEYS = {
  useGetFilterLocationStore: ['MainStore.useGetFilterLocationStore'],
  useGetFilterStoreStatus: ['MainStore.useGetFilterStoreStatus'],
  useGetTotalParticulars: ['MainStore.useGetTotalParticulars']
}

export const useGetFilterLocationStore = () => {
  return useQuery(QUERY_KEYS.useGetFilterLocationStore, async () => {
    return await MainStore.getFilterLocationStore()
  })
}

export const useGetFilterStoreStatus = (data: any) => {
  return useQuery(
    [QUERY_KEYS.useGetFilterStoreStatus, ...Object.values(data)],
    async () => {
      return await MainStore.getFilterStore(data)
    }
  )
}

export const UsePutStoreStatus = () => {
  return useMutation(async (payload: ChangeStore) => {
    return await MainStore.putStoreStatus(payload)
  })
}

export const useGetTotalParticulars = () => {
  return useQuery(QUERY_KEYS.useGetTotalParticulars, async () => {
    return await MainStore.getTotalParticulars()
  })
}