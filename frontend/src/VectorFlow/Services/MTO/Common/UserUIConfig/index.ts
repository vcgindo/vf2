import { useMutation, /*useQuery*/ } from '@tanstack/react-query'
import { UserUIConfigService } from './api'



export const useGetUserUIConfigData = () => {
    return useMutation(async (reportName: any) => {
        return UserUIConfigService.getUserUIReportConfigData(reportName);
    })
}

export const useUpdateUserUIConfigData = () => {
    return useMutation(async (payload: any) => {
        return UserUIConfigService.updateUserUIReportConfigData(payload);
    })
}



