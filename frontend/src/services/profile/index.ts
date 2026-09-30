import { useMutation, useQuery } from '@tanstack/react-query'
import {
  type ChangePassword,
  type ChangeStatus,
  type InfoUser,
  type ChangeTheme
} from '../../types/profile'
import { MainService } from './api'

export const QUERY_KEYS = {
  useGetAllRoles: ['MainService.useGetAllRoles'],
  useGetAllUsers: ['MainService.useGetAllUsers'],
  useGetAllPermissions: ['MainService.useGetAllPermissions'],
  useGetUserPermissions: ['MainService.useGetUserPermissions'],
}

export const useChangePassword = () => {
  return useMutation(async (payload: ChangePassword) => {
    return await MainService.changePassword(payload)
  })
}

export const useGetAllRoles = (onSuccess:any) => {
  return useQuery(QUERY_KEYS.useGetAllRoles, async () => {
    return await MainService.getAllRoles()
  },{onSuccess})
}

export const useGetAllUsers = () => {
  return useQuery(QUERY_KEYS.useGetAllUsers, async () => {
    return await MainService.getAllUsers()
  })
}

export const useGetUserPermissions = () => {
  return useMutation(async (applicationId: any) => {
    return await MainService.getUserPermissions(applicationId)
  })
}


export const useGetAllPermissions = () => {
  return useQuery(QUERY_KEYS.useGetAllPermissions, async () => {
    return await MainService.getAllPermissions()
  })
}

export const useGetRoles = () => {
  return useQuery(QUERY_KEYS.useGetAllRoles, async () => {
    return await MainService.getAllRoles()
  })
}

export const UsePutDeleteUser = () => {
  return useMutation(async (id: string) => {
    return await MainService.putDeleteUser(id)
  })
}

export const useChangeStatus = () => {
  return useMutation(async (data: ChangeStatus) => {
    return await MainService.postChangeStatus(data)
  })
}

export const useResetPwd = () => {
  return useMutation(async (id: string) => {
    return await MainService.postResetPwd(id)
  })
}

export const useRegisterUser = () => {
  return useMutation(async (data: InfoUser) => {
    return await MainService.postRegisterUser(data)
  })
}

export const usePutEditUser = () => {
  return useMutation(async (data: InfoUser) => {
    return await MainService.putEditUser(data)
  })
}

export const useChangeThemeUser = () => {
  return useMutation(async (data: ChangeTheme) => {
    return await MainService.postChangeTheme(data)
  })
}
export const useGetHeadersData = () => {
  return useMutation(async () => {
    return await MainService.getHeadersData()
  })
}

export const usePostUsersDataForValidations = () => {
  return useMutation(async (data: any) => {
    return await MainService.postUsersDataForValidation(data)
  })
}
export const usePostBulkUploadUsers = () => {
  return useMutation(async (data: any) => {
    return await MainService.postBulkUploadUsers(data)
  })
}
