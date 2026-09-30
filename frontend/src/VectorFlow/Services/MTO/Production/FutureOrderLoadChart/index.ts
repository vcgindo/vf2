import { useMutation, useQuery } from '@tanstack/react-query'
import { FutureOrderLoadChartServices,FutureOrderLoadChartPayload } from "./api";


export const QUERY_KEYS = {
    useGetFutureOrderFOLHorizon: ['MDMService.useGetFutureOrderFOLHorizon'],
}


export const useGetFutureOrderLoadChartData = () => {
    return useMutation(async (body: FutureOrderLoadChartPayload) => {
        return FutureOrderLoadChartServices.getFutureOrderLoadChartData(body)
    })
}

export const useGetFutureOrderFOLHorizonDate = () => {
    return useQuery(QUERY_KEYS.useGetFutureOrderFOLHorizon, async () => {
        return await FutureOrderLoadChartServices.getFutureOrderFOLHorizonDate()
    })
  
}

//excel ka
export const useGetFutureOrderLoadChartExcelData = () => {
    return useMutation(async (data: any) => {
        return FutureOrderLoadChartServices.getFutureOrderLoadChartExcelData(data)
    })
}

