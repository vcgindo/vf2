import { useMutation, /*useQuery*/ } from '@tanstack/react-query'
import { MaterialRequirementService } from './api'



export const useGetMaterialRequirementDetails = () => {
    return useMutation(async (data: any) => {
        return MaterialRequirementService.getMaterialRequirementData(data)
    })
}

export const useGetMaterialRequirementDetailsDatewise = () => {
    return useMutation(async (data: any) => {
        return MaterialRequirementService.getMaterialRequirementDataDayWise(data)
    })
}

export const useGetMaterialRequirementDetailsForExcelExport = () => {
    return useMutation(async (params: any) => {
        return MaterialRequirementService.getMaterialRequirementData(params)
    })
}

// export const useGetDate = () => {
  
//     return useQuery(QUERY_KEYS.useGetLatestRunDate, async () => {
//         return await MaterialRequirementService.getLastRunDate();
//     })

// }