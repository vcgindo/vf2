import axios, { AxiosError } from 'axios'
import qs from 'qs'
import { cleanObject, loginRedirect } from '../helpers/utils'
import { MainService } from '../module-main/services/api'
import { installScreenProbe } from '../performance/screenProbe'
import { REQUEST_TIMEOUT_MS, DOWNLOAD_TIMEOUT_MS } from '../helpers/requestDeadline'
import { mtaPublicationBinding as mtaPublication } from './mta-publication-binding'

export const setupAxios = () => {
  installScreenProbe(axios)
  let isRefreshingToken = false
  let isRedirectingForbidden = false
  const requestQueue: any = []

  const processQueue = (token: any, error?: any) => {
    requestQueue.forEach((cb: any) => error ? cb.reject(error) : cb.resolve(token))
    requestQueue.length = 0
  }

  axios.defaults.baseURL = process.env.REACT_APP_API_HOST;
  axios.defaults.withCredentials = true;
  axios.defaults.timeout = REQUEST_TIMEOUT_MS;
  axios.interceptors.request.use(async function (config: any) {
    if (config.responseType === 'blob' && config.timeout === REQUEST_TIMEOUT_MS) {
      config.timeout = DOWNLOAD_TIMEOUT_MS;
    }
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
    return await mtaPublication.request(config)
  })

  axios.interceptors.response.use(mtaPublication.response, async function (error) {
    const originalRequest = error.config
    if (!mtaPublication.isCurrent({ config: originalRequest })) {
      return Promise.reject(new Error('Report refresh was superseded.'));
    }
    mtaPublication.refused(error);
    let errorResp

    if (error.isAxiosError) {
      errorResp = getAxiosError(error)
    } else {
      errorResp = getOtherError(error)
    }

    if (errorResp.status === 403) {
      if (window.location.pathname !== '/permission-forbidden' && !isRedirectingForbidden) {
        isRedirectingForbidden = true
        window.location.href = '/permission-forbidden?URLPermission=true'
      }
      return errorResp
    }

    // A refresh failure cannot queue behind the refresh that owns this request.
    if (errorResp.status === 401 && originalRequest?.url?.includes(MainService.getrefreshTokenUrl())) {
      loginRedirect();
      return Promise.reject(errorResp);
    }

    if (errorResp.status === 401 && !originalRequest._retry && !originalRequest._skipAuthRefresh) {
      originalRequest.headers = originalRequest.headers || {};
      if(errorResp.code === "ERR_BAD_REQUEST" && errorResp.response?.detail === "Authentication credentials were not provided." ) {
        loginRedirect()
        return errorResp;
      }
      
      if (isRefreshingToken) {
        originalRequest._retry = true;
        return await new Promise((resolve, reject) => {
          requestQueue.push({ resolve, reject })
        })
          .then(async (token: any) => {
            if (token?.access) originalRequest.headers.Authorization = `Bearer ${token.access}`;
            else delete originalRequest.headers.Authorization;
            return await axios(originalRequest)
          })
      }

      originalRequest._retry = true
      isRefreshingToken = true

      let token;
      try {
        token = await MainService.refreshToken()
      } catch (error) {
        processQueue(null, error)
        return await Promise.reject(error)
      } finally {
        isRefreshingToken = false
      }
      // The queue belongs only to this refresh, never to its request replay.
      // A later refresh must not be cleared/rejected when this replay settles.
      processQueue(token)
      if (token?.access) originalRequest.headers.Authorization = `Bearer ${token.access}`;
      else {
        delete originalRequest.headers.Authorization;
        if (originalRequest.url.indexOf(MainService.getLogoutUrl()) > -1) loginRedirect();
      }
      return await axios(originalRequest)

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
    error.code === AxiosError.ETIMEDOUT || error.code === AxiosError.ECONNABORTED ||
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
  'The request timed out. Check its result or status before trying again.'
const ERROR_CLIENT =
  'Client error found. Unable to create the HTTP request. Please refresh and try again.'
