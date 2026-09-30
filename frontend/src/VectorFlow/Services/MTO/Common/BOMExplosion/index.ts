import { useMutation, /*useQuery*/ } from '@tanstack/react-query'
import { BOMService } from './api'

export const useGetBOMExplosionData = () => {
    return useMutation(async (data:{orderId: string, lineId: string}) => {
        return BOMService.getBOMExplosionData(data.orderId, data.lineId);
    })
}
