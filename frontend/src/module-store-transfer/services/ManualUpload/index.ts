import { useMutation } from '@tanstack/react-query'
import { ManualUploadService } from './api'

export const QUERY_KEYS = {
  useGetListIST: ['ManualUploadService.useGetListIST']
}

export const useManualUpload = () => {
  return useMutation(async (file: any) => {
    return await ManualUploadService.uploadFile(file)
  })
}
