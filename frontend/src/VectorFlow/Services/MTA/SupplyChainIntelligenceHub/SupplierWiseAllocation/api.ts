/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'
import { SubmitBORRemarkPayload } from '../../../../types/BPR';

export namespace SupplierWiseAllocation {

    export const getSupplierWiseAllocationCount = async (body:any) => {
        return axios.post(process.env.REACT_APP_API_HOST + `api/mta/getSupplierWiseAllocationReportDataCount`,body,{
            headers: { 'Content-Type': 'application/json' }
          })
      }

  
  export const getSupplierWiseAllocationData = async(body:any)=>{
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/getSupplierWiseAllocationReportData`,body,{
      headers:{ 'Content-Type': 'application/json' }
    })
  }

  // export const submitBOROARemark = async (payload:{data:Array<SubmitBORRemarkPayload>}) => {
  //   return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/AddBOROARemark`,{...payload,"forwardUsers":true},{
  //     headers:{ 'Content-Type': 'application/json' }
  //   });
  // }

  // export const getBOROARemarkHistory = async (payload:any) => {
  //   return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetBOROARemarkDetails`,{...payload,"forwardUsers":true},{
  //     headers:{ 'Content-Type': 'application/json' }
  //   }); 
  // }
}


