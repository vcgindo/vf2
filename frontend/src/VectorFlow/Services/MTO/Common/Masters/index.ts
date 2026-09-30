import { useMutation } from '@tanstack/react-query'
import { MasterService } from './api'


export const useGetPlantMasterData = () => {
    return useMutation(async () => {
        return MasterService.getPlantMasterData()
    })
}


export const useGetDeptMasterData = () => {
    return useMutation(async () => {
        return MasterService.getDeptMasterData()
    })
}


export const useGetCCRMasterData = () => {
    return useMutation(async () => {
        return MasterService.getCCRMasterData()
    })
}
