import { useMutation, useQuery } from '@tanstack/react-query'
import { DueDateQuotationService } from './api'

export const QUERY_KEYS = {
    useGetUIConfig: ['MDMService.useGetUIConfig'],
}

export const useGetUIConfig = (reportName: string) => {
    return useQuery(QUERY_KEYS.useGetUIConfig, async () => {
        return DueDateQuotationService.getUIConfig(reportName)
    })
}

interface DDQInputParams {
    page: number,
    unSch: boolean,
    appliedFilters: any
    page_size?:number
}


export const useGetFilteredOrdersForDDQ = () => {
    return useMutation(async (data: DDQInputParams ) => {
        return DueDateQuotationService.getFilteredOrdersForDDQ(data)
    })
}

export const useGetBufferMasterData = () => {
    return useMutation(async () => {
        return DueDateQuotationService.getBufferMasterData()
    })
}

export const useGetCCRGroupMaster = () => {
    return useMutation(async () => {
        return DueDateQuotationService.getCCRGroupMaster()
    })
}


export const useGetRouteDetails = () => {
    return useMutation(async (route_id: number) => {
        return DueDateQuotationService.getRouteDetails(route_id)
    })
}

export const useGetCCRItemTypeMappingMaster = () => {
    return useMutation(async () => {
        return DueDateQuotationService.getCCRItemTypeMappingMaster()
    })
}
export const useGetFOLData = () => {
    return useMutation(async () => {
        return DueDateQuotationService.getFOLData()
    })
}
export const useGetCCRMasterData = () => {
    return useMutation(async () => {
        return DueDateQuotationService.getCCRMasterData()
    })
}

export const useGetDailyWorkingCalendar = () => {
    return useMutation(async () => {
        return DueDateQuotationService.getDailyWorkingCalendar()
    })
}

export const useGetMarketOperatingLeadTimeMasterData = () => {
    return useMutation(async () => {
        return DueDateQuotationService.getMarketOperatingLeadTimeMasterData()
    })
}

export const useGetLineCCRDetails = () => {
    return useMutation(async (body: string[]) => {
        return DueDateQuotationService.getLineCCRDetails(body)
    })
}


export const useUpdateBuffRouteCCREstDate = () => {
    return useMutation(async (body: {bufferData: any, routeData: any}) => {
        return DueDateQuotationService.updateBuffRouteCCREstDate(body)
    })
}

export const useUpdateScheduleOrders = () => {
    return useMutation(async (body: {orders:any}) => {
        return DueDateQuotationService.updateScheduleOrders(body)
    })
}

export const useGetOrdersForExcelDDQ = () =>{
    return useMutation(async (data: any) => {
        return DueDateQuotationService.getFilteredOrdersForExcelDDQ(data)
    })
}

export const useGetDDQAnalytics = ()=>{
    return useMutation(async () => {
        return DueDateQuotationService.getDDQAnalyticsData()
    })
}

