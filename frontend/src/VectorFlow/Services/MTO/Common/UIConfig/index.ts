import { useMutation, /*useQuery*/ } from '@tanstack/react-query'
import { getUIAndUserConfigDataPayload, UIConfigService } from './api'



export const useGetUIConfigData = () => {
    return useMutation(async (reportName: any) => {
        return UIConfigService.getUIConfigData(reportName);
    })
}

export const useGetUIAndUserConfigData = () => {
    return useMutation(async (payload: getUIAndUserConfigDataPayload) => {
        return UIConfigService.getUIAndUserConfigData(payload);
    })
}



