import { useMutation, /*useQuery*/ } from '@tanstack/react-query'
import { STPLAndFullKitService } from './api'

export const useGetSTPLAndFullKitData = () => {
    return useMutation(async (params: any) => {
        return STPLAndFullKitService.getSTPLandFullkitInDaysData(params);
    })
}

export const useGetSTPLAndFullKitExcelData = () => {
    return useMutation(async (params: any) => {
        return STPLAndFullKitService.getSTPLandFullkitInDaysExcelData(params);
    })
}