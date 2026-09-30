import { Forced } from './api'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  type ChangeItemTerminate,
  type getContactDetail
} from './../../types/forced'

export const QUERY_KEYS_FORCED = {
  useGetContactDetail: ['Forced.useGetContactDetail'],
  getProductForcedClose: ['getProductForcedClose'],
  useGetDataExcel: ['useGetDataExcel'],
  useGetIdData: ['useGetIdData'],
  useGetAgeingData: ['useGetAgeingData'],
  useGetParticulars: ['useGetParticulars']
}

export const GetProductForcedClose = (params: any) => {
  return useQuery(QUERY_KEYS_FORCED.getProductForcedClose, async () => {
    return await Forced.GetProductForced(params)
  })
}

export const UsePutItemTerminate = () => {
  return useMutation(async (payload: ChangeItemTerminate) => {
    return await Forced.putItemTerminate(payload)
  })
}

export const useGetContactDetail = (data: getContactDetail) => {
  return useQuery(QUERY_KEYS_FORCED.useGetContactDetail, async () => {
    return await Forced.getContactDetail(data)
  })
}

export const useGetDataExcel = (params: any) => {
  return useQuery(QUERY_KEYS_FORCED.useGetDataExcel, async () => {
    return await Forced.getDataExcel(params)
  })
}

export const useGetIdData = (params: any) => {
  return useQuery(QUERY_KEYS_FORCED.useGetIdData, async () => {
    return await Forced.getIdData(params)
  })
}

export const useGetAegingData = () => {
  return useQuery(QUERY_KEYS_FORCED.useGetAgeingData, async () => {
    return await Forced.getAgeing()
  })
}

export const useGetParticularsForced = () => {
  return useQuery(QUERY_KEYS_FORCED.useGetParticulars, async () => {
    return await Forced.getParticulars()
  })
}