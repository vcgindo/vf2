/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'

export namespace PlanningService {

    export const getPlanningDataCount = async (body:any) => {
        return axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetPlanningDataCount`,body,{
            headers: { 'Content-Type': 'application/json' }
          })
      }

    export const getPlanningDataGraph = async (body:any) => {
        return axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetPlanningDataGraph`,body,{
            headers: { 'Content-Type': 'application/json' }
            })
    }

    export const getPlanningDataGrid = async (body:any) => {
        return axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetPlanningDataGrid`,body,{
            headers: { 'Content-Type': 'application/json' }
            })
    }

    export const getPlanningDataCustom = async (body:any) => {
        return axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetPlanningDataCustom`,body,{
            headers: { 'Content-Type': 'application/json' }
            })
    }

    export const submitOpenExpediteRequest = async (body:any) => {
        return axios.post(process.env.REACT_APP_API_HOST + `api/mta/SubmitOpenExpediteRequest`,{...body, "forwardUsers":true},{
            headers: { 'Content-Type': 'application/json' }
            })
    }

    export const getPlanningDataGridCount = async (body:any) => {
        return axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetPlanningDataGridCount`,body,{
            headers: { 'Content-Type': 'application/json' }
        })
    }

}