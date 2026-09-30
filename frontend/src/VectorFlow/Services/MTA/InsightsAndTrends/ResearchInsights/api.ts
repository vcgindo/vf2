/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'

export namespace ResearchInsightsService {
    export const getUpdatedGraphData = async (body:any) => {
        return axios.post(process.env.REACT_APP_API_HOST +`api/mta/GetResearchInsightData`,body,{
            headers: { 'Content-Type': 'application/json' }
        })      
    }

    export const getHistoricalAvailabilityData = async()=>{
        return await axios.get(process.env.REACT_APP_API_HOST + `api/mta/GetHistroricalAvailabilityBPRData`,{
            headers: { 'Content-Type': 'application/json' }
          })
    }

}