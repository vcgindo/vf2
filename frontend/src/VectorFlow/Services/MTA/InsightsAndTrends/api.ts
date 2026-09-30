/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios';
export namespace InsightsAndTrendsService{
export const getAvaialabilityTrend = async (body:{horison:number}) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/AvailabilityTrend`,body,{
      headers: { 'Content-Type': 'application/json' }
    })
  }
  export const getChronicUnavailabilityLoc = async () => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/ChronicUnavailabilityLoc`,{},{
      headers: { 'Content-Type': 'application/json' }
    })
  }
  export const getChronicUnavailabilitySku = async () => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/ChronicUnavailabilitySku`,{},{
      headers: { 'Content-Type': 'application/json' }
    })
  }
  export const getAvailabilityAgeing = async (body:{horison:number}) => {
    //console.log(horizon);
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/AvailabilityAgeing`,body,{
      
      headers: { 'Content-Type': 'application/json' }
    })
  }
  export const getDBMNormSuggestionLoc = async () => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/DBMNormSuggestionLoc`,{},{
      headers: { 'Content-Type': 'application/json' }
    })
  }
  export const getDBMNormSuggestionPie = async () => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/DBMNormSuggestionPie`,{},{
      headers: { 'Content-Type': 'application/json' }
    })
  }
  export const getDBMNormSuggestionSKUs = async () => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/DBMNormSuggestionSKUs`,{},{
      headers: { 'Content-Type': 'application/json' }
    })
  }
  export const getDBMNormSuggestionAgeing = async () => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/DBMNormSuggestionAgeing`,{},{
      headers: { 'Content-Type': 'application/json' }
    })
  }
 
  export const getExcessInventorySku = async (body:{horison:number}) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/ExcessInventorySku`,body,{
      headers: { 'Content-Type': 'application/json' }
    })
  }
  export const getExcessInventoryValue = async (body:{horison:number}) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/ExcessInventoryValue`,body,{
      headers: { 'Content-Type': 'application/json' }
    })
  }
  export const getChronicUnavailabilityGridView = async (body:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/ChronicUnavailabilityGridViewData`,body,{
      headers: { 'Content-Type': 'application/json' }
    })
  }
 
}