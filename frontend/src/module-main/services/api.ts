/* eslint-disable @typescript-eslint/no-namespace */
import { type ChangePassRequest } from '../types/User'
import axios from 'axios'
import { type RegisterRequest, type LoginRequest } from '../types'
import { LOCAL_STORAGE_KEY } from '../../helpers/constants'
import { type QueryClient } from '@tanstack/react-query'
import { isEmpty } from 'lodash'

const API_USER = 'api/user'

interface Token {
  tokenType?: string
  access?: string
  refresh?: string
  expiryAt?: number
  apigeeToken: { access_token: string }
}

export const expandBrowserRoutePermissions = (permissions: string[] = []) => {
  const expanded = new Set<string>()

  permissions.forEach((permission) => {
    if (!permission) return

    const value = permission.trim()
    expanded.add(value)

    const gatewayRoute = value.match(/^\/?(?:mta|mto)(\/.*)$/i)
    if (gatewayRoute) expanded.add(gatewayRoute[1])
  })

  return Array.from(expanded)
}

export namespace MainService {
  export const acquireToken = async () => {
    let token: Token
    try {
      token = JSON.parse(
        localStorage.getItem(LOCAL_STORAGE_KEY.TOKEN_PAYLOAD) || '{}'
      )
      // if (token.expiryAt && token.accessToken && token.refreshToken) {
      //   // minus 20 seconds for network latency
      //   if (new Date(token.expiryAt - 20 * 1000) > new Date()) {
      //     return token;
      //   }
      //   console.log('token expired, requesting a new token', 'expired at', new Date(token.expiryAt));
      //   return refreshToken(token.refreshToken);
      // } else {
      //   return undefined;
      // }
      return isEmpty(token) ? undefined : token
    } catch {
      // in case token modified by human
      return undefined
    }
  }

  // get a new access_token by refresh_token
  export const refreshToken = async () => {
    try {
      const response = await axios.post<Token>(getrefreshTokenUrl(), {}, { _skipAuthRefresh: true } as any)
      const token: any = response?.data
      localStorage.setItem(
        LOCAL_STORAGE_KEY.TOKEN_PAYLOAD,
        JSON.stringify(token?.data?.token || {})
      )
      return token?.data?.token
    } catch (error) {
      console.log(error)
      //  refresh token not valid or expired
      throw error
    }
  }

  export const logout = async (
    isUnauthorizedOrQueryClient: boolean | QueryClient = false,
    suppliedQueryClient?: QueryClient
  ) => {
    const queryClient = typeof isUnauthorizedOrQueryClient === 'boolean'
      ? suppliedQueryClient
      : isUnauthorizedOrQueryClient
    let response
    try {
      // The refresh token is held in an HttpOnly cookie.
      response = await axios.post(getLogoutUrl(), {}, { _skipAuthRefresh: true } as any)
    } finally {
      queryClient?.clear()
      localStorage.removeItem(LOCAL_STORAGE_KEY.TOKEN_PAYLOAD)
      localStorage.removeItem(LOCAL_STORAGE_KEY.URL_PERMISSION)
      localStorage.removeItem('isCheckLogin')
    }
    return response
  }

  export const getrefreshTokenUrl = () => {
    return `/${API_USER}/token/refresh/`
  }

  export const getLogoutUrl = () => {
    return `/${API_USER}/logout/`
  }

  export const register = async (payload: RegisterRequest) => {
    return await axios.post(`/${API_USER}/register/`, payload)
  }

  export const login = async (payload: LoginRequest) => {
    return await axios
      .post(`/${API_USER}/login/`, payload)
      .then(async (resp) => {
        const urlPermissions = expandBrowserRoutePermissions(
          resp?.data?.data?.url_permission
        )

        // The backend intentionally keeps JWTs in HttpOnly cookies. Keep a
        // non-secret marker for the existing route guards instead of storing
        // the string "undefined", which also broke logout JSON parsing.
        localStorage.setItem(
          LOCAL_STORAGE_KEY.TOKEN_PAYLOAD,
          JSON.stringify(resp?.data?.data?.token || {})
        )
        localStorage.setItem(
          LOCAL_STORAGE_KEY.URL_PERMISSION,
          JSON.stringify(urlPermissions)
        )
        localStorage.setItem(
          LOCAL_STORAGE_KEY.LANDING_PAGE,
          resp?.data?.data?.landing_page
        )
        localStorage.setItem(
          LOCAL_STORAGE_KEY.User_ID,
          resp?.data?.data?.user?.id
        )
        localStorage.setItem(
          LOCAL_STORAGE_KEY.User_Name,
          resp?.data?.data?.user?.name
        )
        return await Promise.resolve(resp)
      })
  }

  export const forgotPassword = async (payload: { email: string }) => {
    return await axios.post(`/${API_USER}/send-email-reset-pwd/`, payload)
  }
  export const changePassword = async (payload: ChangePassRequest) => {
    return await axios.post(
      `/${API_USER}/forgot-password/${payload.uid}/${payload.token}`,
      payload
    )
  }

  export const getProfile = async () => {
    const response = await axios.get(`/${API_USER}/profile/`)
    const profile = response?.data?.data

    if (profile) {
      profile.url_permission = expandBrowserRoutePermissions(
        profile.url_permission
      )
      localStorage.setItem(
        LOCAL_STORAGE_KEY.URL_PERMISSION,
        JSON.stringify(profile.url_permission)
      )
    }

    return response
  }
  export const getProductFilter = async (url: string) => {
    return await axios.get(url)
  }
  export const getTotalPaticulars = async () => {
    return await axios.get('/api/ist/total-paticulars')
  }
}
