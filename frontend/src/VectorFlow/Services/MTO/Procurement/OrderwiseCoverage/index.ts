import { useMutation, /*useQuery*/ } from '@tanstack/react-query'
import { OrderwiseCoverageService } from './api'

export const QUERY_KEYS = {
    useGetOrderSchedulingData: ['MDMService.useGetOrderSchedulingData']
}

export const useGetOrderwiseCoverageData = () => {
    return useMutation(async (props: { page?: number, graph: number, appliedFilters?: any,page_size?:any }) => {
        return OrderwiseCoverageService.getOrderwiseCoverageData(props)
    })
}

export const useGetOrderwiseCoverageDataForExcelExport = () => {
    return useMutation(async (params : any) => {
        return OrderwiseCoverageService.getOrderwiseCoverageDataForExcelExport(params)
    })
}



