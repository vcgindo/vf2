import { useMutation, /*useQuery*/ } from '@tanstack/react-query'
import { DBRSettingsService } from './api'

export const useGetDBRsettingsData = () => {
    return useMutation(async () => {
        return DBRSettingsService.getDBRsettingsData()
    })
}


