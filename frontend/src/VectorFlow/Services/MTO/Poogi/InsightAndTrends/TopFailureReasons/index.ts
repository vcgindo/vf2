import { useMutation, /*useQuery*/ } from '@tanstack/react-query'
import { TopFailureReasonsService } from './api'

export const useTopFailureData = () => {
    return useMutation(async (params: any) => {
        return TopFailureReasonsService.getTopFailureData(params);
    })
}
