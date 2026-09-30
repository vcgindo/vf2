import {useMutation } from '@tanstack/react-query'
import { InTransitWhereAboutsService } from './api'


export const QUERY_KEYS = {
 
}

export const useGetInTransitWhereAboutsDataCount = () => {
  return useMutation(async (body:any) => {
    return await InTransitWhereAboutsService.getInTransitWhereAboutsDataCount(body)
  });
}

export const useGetInTransitWhereAboutsData = () => {
  return useMutation(async (body:any) => {
    return await InTransitWhereAboutsService.getInTransitWhereAboutsData(body)
  });
}

export const useGetRemarkDetailsForInTransit = () => {
  return useMutation(async (body:any) => {
    return await InTransitWhereAboutsService.getRemarkDetailsForInTransit(body)
  });
}

export const useSubmitRemarksForInTransit = () => {
  return useMutation(async (body:any) => {
    return await InTransitWhereAboutsService.submitRemarksForInTransit(body)
  });
}

export const useGetTransporterDetails = () => {
  return useMutation(async (body:any) => {
    return await InTransitWhereAboutsService.getTransporterDetails(body)
  });
}