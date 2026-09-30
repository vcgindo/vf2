import { useMutation, /*useQuery*/ } from '@tanstack/react-query'
import { TrendsFailureReasonsService } from './api'

export const useTopFailureReasonData = () => {
    return useMutation(async (params: any) => {
        return TrendsFailureReasonsService.getTrendsFailureData(params);
    })
}
