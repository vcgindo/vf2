import { type LoginRequest } from '../types/User'
import { useMutation, useQuery } from '@tanstack/react-query'
import { type RegisterRequest } from '../types'
import { MainService } from './api'

export const QUERY_KEYS = {
  useGetProfile: ['MainService.useGetProfile'],
  useGetProductFilter: ['MainService.useGetProductFilter'],
  useGetLocation: ['MainService.useGetLocation'],
  UseGetIstTotal: ['MainService.useGetTotal']
}

export const useRegisterAccount = () => {
  return useMutation(async (payload: RegisterRequest) => {
    return await MainService.register(payload)
  })
}
export const useLoginAccount = () => {
  return useMutation(async (payload: LoginRequest) => {
    return await MainService.login(payload)
  })
}

export const useForgotPassword = () => {
  return useMutation(async (payload: { email: string }) => {
    return await MainService.forgotPassword(payload)
  })
}

export const useChangePassword = () => {
  return useMutation(
    async (payload: { uid: string, token: string, new_password: string, confirm_password: string }) => {
      return await MainService.changePassword(payload)
    }
  )
}

export const useGetProfile = () => {
  return useQuery(QUERY_KEYS.useGetProfile, async () => {
    return await MainService.getProfile()
  })
}

// export const useGetProductFilter = () => {
//   return useQuery(QUERY_KEYS.useGetProductFilter, () => {
//     return MainService.getProductFilter()
//   })
// }
export const UseGetIstTotal = () => {
  return useQuery(QUERY_KEYS.UseGetIstTotal, async () => {
    return await MainService.getTotalPaticulars()
  })
}
