import axios, { AxiosError } from 'axios'
import qs from 'qs'
import { cleanObject, loginRedirect } from '../helpers/utils'
import { MainService } from '../module-main/services/api'

export const setupAxios = () => {
  let isRefreshingToken = false
  const requestQueue: any = []

  const processQueue = (token: any) => {
    requestQueue.forEach((cb: any) => cb.resolve(token))
    requestQueue.length = 0
  }

  axios.defaults.baseURL = process.env.REACT_APP_API_HOST;
  axios.defaults.withCredentials = true;
  axios.interceptors.request.use(async function (config: any) {
    if (config.url && (!config.headers || !config.headers['Authorization'])) {
      const token = await MainService.acquireToken();

      const userId = localStorage.getItem('User-ID')
      const userName = localStorage.getItem('User-Name')
      config.headers = {
        ...config.headers,
        ...(userId ? { 'User-ID': userId } : {}),
        ...(userName ? { 'User-Name': userName } : {})
      }

      if (!token) {
        if (config.url.indexOf(MainService.getLogoutUrl()) > -1) {
          loginRedirect();
        }
      } else {
        config.headers = {
          ...config.headers,
          Authorization: `Bearer ${token?.access}`
        }
      }
    }
    return config
  })

  axios.interceptors.response.use(undefined, async function (error) {
    const originalRequest = error.config
    let errorResp

    if (error.isAxiosError) {
      errorResp = getAxiosError(error)
    } else {
      errorResp = getOtherError(error)
    }

    if (errorResp.status === 403) {
      window.location.href = '/permission-forbidden?URLPermission=true'
      return errorResp
    }

    if (errorResp.status === 401 && !originalRequest._retry) {
      if(errorResp.code === "ERR_BAD_REQUEST" && errorResp.response.detail === "Authentication credentials were not provided." ) {
        loginRedirect()
        return errorResp;
      }
      
      if (
        errorResp.response.code === 'token_not_valid' &&
        originalRequest.url.indexOf(MainService.getrefreshTokenUrl()) > -1
      ) {        
        loginRedirect()
        return
      }
      if (isRefreshingToken) {
        return await new Promise((resolve, reject) => {
          requestQueue.push({ resolve, reject })
        })
          .then(async (token: any) => {
            originalRequest.headers = {
              ...originalRequest.headers,
              Authorization: `Bearer ${token?.access}`
            }
            return await axios(originalRequest)
          })
          .catch(async (err) => {
            return err
          })
      }

      originalRequest._retry = true
      isRefreshingToken = true

      try {
        const token = await MainService.refreshToken()
        if (!token) {
          if (originalRequest.url.indexOf(MainService.getLogoutUrl()) > -1) {
            loginRedirect()
          }
        } else {
          originalRequest.headers = {
            ...originalRequest.headers,
            Authorization: `Bearer ${token?.access}`
          }
        }

        const result = await axios(originalRequest)
        processQueue(token)
        return result
      } catch (error) {
        processQueue(null)
        return error
      } finally {
        isRefreshingToken = false
      }

    }

    if (errorResp.status === 400) {
      // alert(JSON.stringify(error.response.data))
      return errorResp
    }
    
    return await Promise.reject(errorResp);
  })

  axios.defaults.paramsSerializer = {
    serialize: (params) => qs.stringify(cleanObject(params))
  }
}

const getOtherError = (error: any) => {
  const path = window.location.pathname
  if (typeof error === 'string') {
    return { message: error, path }
  } else if (!error.message) {
    console.error(error)
    return { message: ERROR_GENERAL, path }
  } else {
    console.error(error)
    return error
  }
}

const getAxiosError = (error: any) => {
  let message

  if (error.code === AxiosError.ERR_NETWORK) {
    message = ERROR_NETWORK
  } else if (
    error.code === AxiosError.ETIMEDOUT ||
    error.response?.status === 504
  ) {
    message = ERROR_TIMEOUT
  } else if (error.response) {
    message = error.response.data?.message
      ? error.response.data.message
      : ERROR_GENERAL

    switch (error.response.status) {
      case 401:
        message = 'You are not authorized to access this resource!'
        break
      case 403:
        message = "You don't have permission to access the resource!"
        break
      case 404:
        message = 'The requested resource does not exist or has been deleted!'
        break
      case 500:
        message = ERROR_GENERAL
        break
    }
  } else if (!error.request) {
    message = ERROR_CLIENT
  }

  return {
    code: error.code,
    status: error.response?.status,
    error: error.response?.data?.error || error.response?.data.email?.[0],
    message,
    path: error.config?.url,
    validation: error.response?.data?.validation,
    response: error.response?.data,
    traceError: error.response?.data?.message,
    timestamp: error.response?.data?.timestamp || new Date()
  }
}

const ERROR_GENERAL = 'Something went wrong and the request was not completed!'
const ERROR_NETWORK =
  'Network error, please check your network connectivity and try again.'
const ERROR_TIMEOUT =
  'Looks like the server is taking too long to respond. The system is still processing your request in the background. Please check the result later or try again.'
const ERROR_CLIENT =
  'Client error found. Unable to create the HTTP request. Please refresh and try again.'
