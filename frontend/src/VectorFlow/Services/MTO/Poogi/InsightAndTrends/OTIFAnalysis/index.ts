import { useMutation, /*useQuery*/ } from '@tanstack/react-query'
import { OTIFAanalysisService } from './api'

export const useGetOTIFAnalysisData = () => {
    return useMutation(async (params: any) => {
        return OTIFAanalysisService.getOTIFAnalysisData(params);
    })
}

export const useGetOTIFAnalysisDataExcelExport = () => {
    return useMutation(async (params: any) => {
            return OTIFAanalysisService.getOTIFAnalysisDataExcelExport(params);
        })
}

