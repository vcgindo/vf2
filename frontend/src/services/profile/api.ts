/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'
import {
  type ChangePassword,
  type ChangeStatus,
  type InfoUser,
  type ChangeTheme
} from '../../types/profile'

const API_USER = 'api/user'

export namespace MainService {
  export const changePassword = async (payload: ChangePassword) => {
    return await axios.post(`/${API_USER}/change-pwd/`, payload)
  }

  export const getAllRoles = async () => {
    return await axios.get(`${API_USER}/all-role/`)
  }

  export const getUserPermissions = async (payload:any) => {
    return await axios.get(`${API_USER}/get-user-permissions/?id=${payload}`)
   }

  export const getAllUsers = async () => {
    return await axios.get(`${API_USER}/all-users/`)
  }

  export const getAllPermissions = async () => {
    return await axios.get(`${API_USER}/all-permissions/`)
  }

  export const putDeleteUser = async (id: any) => {
    return await axios.put(`${API_USER}/soft-delete/${id}`)
  }

  export const postChangeStatus = async (data: ChangeStatus) => {
    return await axios.post(`/${API_USER}/change-active`, data)
  }

  export const postResetPwd = async (id: string) => {
    return await axios.post(`${API_USER}/reset-pwd/${id}`)
  }

  export const postRegisterUser = async (data: InfoUser) => {
    return await axios.post(`${API_USER}/register/`, data)
  }

  export const putEditUser = async (data: InfoUser) => {
    return await axios.put(`${API_USER}/edit-user`, data)
  }

  export const postChangeTheme = async (data: ChangeTheme) => {
    return await axios.post(`${API_USER}/change-theme`, data)
  }

  export const getIssueReport = async () => {
    return await axios.get(`${API_USER}/issue-report/`)
  }

  export const postIssueReport = async (data: any) => {
    return await axios.post(`${API_USER}/issue-report/`, data)
  }
  export const getHeadersData = async () => {
    return await axios.get(`${API_USER}/get-headers-data/`)
  }

  export const postUsersDataForValidation = async (data:any)=>{
    return await axios.post(`${API_USER}/bulkUploadUsers/`, data)
  }

  export const postBulkUploadUsers = async (data:any)=>{
    return await axios.post(`${API_USER}/bulkUsersRegister/`, data)
  }
}
