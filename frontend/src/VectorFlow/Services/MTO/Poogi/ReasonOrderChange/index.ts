import { useQuery, useMutation } from '@tanstack/react-query'
import { ReasonOrderChangeServices } from './api'

//useQuery for get 
export const QUERY_KEYS = {
    useGetReasonForAnalyticDelayOrder: ['MDMService.useGetReasonForAnalyticDelayOrder'],
    useGetReasonForDelayOrder: ['MDMService.useGetReasonForDelayOrder'],
    useGetPoogiMajorMinorReason: ['MDMService.useGetPoogiMajorMinorReason']
}

export const useGetReasonForPoogiAnalytics = () => {
    return useQuery(QUERY_KEYS.useGetReasonForAnalyticDelayOrder, async () => {
        return await ReasonOrderChangeServices.getPoogiReasonsAnalyticalData()
    })
}

export const useGetReasonForDelayOrder = () => {
    return useMutation(async (data: {wip:number,curr:number, pageSize?:number,appliedFilters?:any}) => {
        return await ReasonOrderChangeServices.getPoogiReasonsDelayedOrder(data)
    })
}

export const useGetPoogiRemarks = () => {
    return useMutation(async (data: string) => {
        return await ReasonOrderChangeServices.getPoogIRemarks(data);
    })
}

export const useGetPoogiMajorMinorReason = () => {
    return useQuery(QUERY_KEYS.useGetPoogiMajorMinorReason, async () => {
        return await ReasonOrderChangeServices.getPoogiMajorMinorReason();
    })
}

export const usePutPoogiRemarks = () => {
    return useMutation(async (data: any) => {
        return await ReasonOrderChangeServices.updatePoogiRemarks(data);
    })
}

export const useGetPoogReasonForDealyedOrderExcel = () => {
    return useMutation(async (data: any) => {
        return await ReasonOrderChangeServices.getPoogiReasonsDelayedOrderExcelExport(data);
    })
}


