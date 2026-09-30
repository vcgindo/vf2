/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'

export namespace ISTStatusService {
  export const getListComponent = async () => {
    return await axios.get('/api/ist/mapping-columns')
  }

  export const getListView = async () => {
    return await axios.get('/api/ist/status/list-views')
  }

  export const getViewDetailById = async (view_id: number) => {
    return await axios.get(`/api/ist/status/view-data/${view_id}`)
  }

  export const createView = async (viewName: string) => {
    return await axios.post('/api/ist/status/create-views', {
      view_name: viewName,
      columns_list: ['donor_wh_location_group', 'donor_wh_name', 'product_hierarchy_3'],
      is_default_view: true
    })
  }

  export const exportAll = async (view_id: number) => {
    return await axios.get(`/api/ist/status/exports-all/${view_id}`)
  }

  export const updateView = async (view_id: number, viewData: object) => {
    return await axios.put(`/api/ist/status/update-view/${view_id}`, viewData)
  }

  export const deleteView = async (view_id: number) => {
    return await axios.delete(`/api/ist/status/delete-view/${view_id}`)
  }
}
