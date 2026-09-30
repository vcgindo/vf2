import { useMutation } from '@tanstack/react-query'
import { ResourceUtilizationService } from './api'

export const useGetResourceUtilizationData = () => {
    return useMutation(async (data: any) => {
        return ResourceUtilizationService.getResourceUtilizationData(data?.startDate, data?.endDate, data?.ccrName, data?.plantName, data?.deptName)
    })
}


