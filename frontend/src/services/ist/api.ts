/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'
import { type ChangeType } from './../../types/ist'
const API_IST = 'api/ist/pending'

export namespace ISTService {
  export const getLocationFilter = async (url: string) => {
    return await axios.get(url)
  }

  export const getPendingFilter = async (body: any) => {
    return await axios({
      method: 'post',
      url: `/${API_IST}/filter`,
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify(body)
    })
  }
  export const putItemCodeChangeType = async (payload: ChangeType) => {
    return await axios.put(`/${API_IST}/change-ist-type`, payload)
  }
  export const getReceiverFilter = async (url: string) => {
    return await axios.get(url)
  }
  export const getDownloadTemp = async () => {
    return await axios.get('/api/manual-upload/template-view/')
  }
  export const getLocationFilterList = async (url: string) => {
    return await axios.get(url);
  }
}
