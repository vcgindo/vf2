/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'
import {
  type ChangeItemTerminate,
  type getContactDetail
} from './../../types/forced'

const API_FORCED = 'api/forced-closure'

export namespace Forced {
  export const GetProductForced = async (body: any) => {
    return await axios({
      method: 'post',
      url: `/${API_FORCED}/filter-forced-closure`,
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify(body)
    })
  }

  export const putItemTerminate = async (payload: ChangeItemTerminate) => {
    return await axios.put(`/${API_FORCED}/change-status-closure`, payload)
  }
  export const getContactDetail = async (data: getContactDetail) => {
    return await axios({
      method: 'get',
      url: `/${API_FORCED}/contact-detail`,
      params: data
    })
  }
  export const getDataExcel = async (body: any) => {
    return await axios({
      method: 'post',
      url: `/${API_FORCED}/export-closure`,
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify(body)
    })
  }
  export const getIdData = async (params: any) => {
    return await axios({
      method: 'get',
      url: `/${API_FORCED}/get-id`,
      params
    })
  }

  export const getAgeing = async () => {
    return await axios.get(`/${API_FORCED}/get-ageing`)
  }

  export const getParticulars =async () => {
    return await axios.get(`/${API_FORCED}/get-particulars`)
  }
}
