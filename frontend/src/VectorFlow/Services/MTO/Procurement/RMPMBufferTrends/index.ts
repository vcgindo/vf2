import { useMutation, /*useQuery*/ } from '@tanstack/react-query'
import { RMPMBufferTrendsService } from './api'


export const useGetRMPMBufferTrendsData = () => {
    return useMutation(async (params:any) => {
        return RMPMBufferTrendsService.getRMPMBufferTrendsData(params)
    })
}