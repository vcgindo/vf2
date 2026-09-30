/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'
import { type ChangeStore } from './../../types/store'
const API_STORE = '/api/store-status'
export namespace MainStore {
  export const getFilterLocationStore = async () => {
    return await axios.get(`${API_STORE}/filter-location/`)
  }
  export const getFilterStore = async (body: any) => {
    return await axios({
      method: 'post',
      url: `${API_STORE}/filter-store-status/`,
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify(body)
    })
  }
  export const putStoreStatus = async (payload: ChangeStore) => {
    return await axios.put(`${API_STORE}/change-store-status/`, payload)
  }
  export const getTotalParticulars =async () => {
    return await axios.get(`${API_STORE}/total-particulars/`)
  } 
}
