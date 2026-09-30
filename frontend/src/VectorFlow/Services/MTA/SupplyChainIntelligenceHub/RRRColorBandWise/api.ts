/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'


export namespace RRRColorBandWiseService {

    export const getRRRColorBandWiseRecordCount = async (body:any) => {
        return axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetRRRAllocationReportDataCount`,body,{
            headers: { 'Content-Type': 'application/json' }
          })
      }

  
  export const getRRRColorBandWiseData = async(body:any)=>{
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetRRROrderAllocationReportData`,body,{
      headers:{ 'Content-Type': 'application/json' }
    })
  }
}


