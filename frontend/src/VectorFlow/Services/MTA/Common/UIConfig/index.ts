import { useMutation, /*useQuery*/ } from '@tanstack/react-query'
import { UIConfigService } from './api'

export const useGetUIConfigData = () => {
    return useMutation(async (reportName: any) => {
        return UIConfigService.getUIConfigData(reportName);
    })
}



