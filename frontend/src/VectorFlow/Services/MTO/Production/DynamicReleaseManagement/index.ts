import { useMutation, /*useQuery*/ } from '@tanstack/react-query'
import { DynamicReleaseManagementService } from './api'

export const QUERY_KEYS = {
    useGetDynamicReleaseData: ['MDMService.useGetDynamicReleaseData']
}

export const useGetDynamicReleaseData = () => {
    return useMutation(async (data: { graph: number, ao: number, page: number, appliedFilters: any,page_size?:any, wipObj?:any}) => {

        return DynamicReleaseManagementService.getDynamicReleaseData(data)


    })
}

export const useSaveRouteData = () => {
    return useMutation(async (params: any) => {

        return DynamicReleaseManagementService.saveRouteData(params)


    })
}
export const useUpdateDynamicReleaseData = () => {
    return useMutation(async (body: any) => {

        return DynamicReleaseManagementService.updateDynamicReleaseData(body)


    })
    
}
export const useGetDynamicReleaseExcelData = () => {
    return useMutation(async (params: any) => {
        return DynamicReleaseManagementService.getDynamicReleaseExcelData(params);
    })
}

export const useFetchFOLGap = () => {
    return useMutation(async (params: any) => {
        return DynamicReleaseManagementService.FetchFOLGap(params);
    })
}


