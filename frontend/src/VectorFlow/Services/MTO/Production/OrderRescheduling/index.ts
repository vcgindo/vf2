import { useMutation, /*useQuery*/ } from '@tanstack/react-query'
import { OrderReschedulingService } from './api'

export const QUERY_KEYS = {
    useGetOrderSchedulingData: ['MDMService.useGetOrderSchedulingData']
}


export const useGetOrderSchedulingPageData = () => {
    return useMutation(async ({pageNum
           , pageSize,appliedFilters}:any) => {
        return OrderReschedulingService.getOrderReschedulingPageData(pageNum,pageSize,appliedFilters);
    })
}

export const useGetOrderSchedulingExcelData = () => {
    return useMutation(async (args: {body: any, isExcelExport: any, report_name : any}) => {
        return OrderReschedulingService.getOrderReschedulingExcelData(args);
    })
}


export const usePutUpdateOrderDueDate = () => {
    return useMutation(async (body: any) => {
        return OrderReschedulingService.putUpdateOrderDueDate([body]);
    })
}

export const useGetHolidaysForMaxFolCCROfOrder = () => {
    return useMutation(async (orderId: number) => {
        return OrderReschedulingService.getHolidaysForMaxFolCCROfOrder(orderId)
    })
}

