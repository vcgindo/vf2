import { useMutation } from '@tanstack/react-query'


import { SupplierWiseAllocation } from './api'
import { BORDataPayload, SubmitBORRemarkPayload } from '../../../../types/BPR';

export const QUERY_KEYS = {
//   useGetBPRUIConfiguration: ['BPRService.useGetBPRUIConfiguration'],
}



export const useGetSupplierWiseAllocationCount =()=>{
  return useMutation(async(body:any)=>{
    return await SupplierWiseAllocation.getSupplierWiseAllocationCount(body)
  })
}

export const useGetSupplierWiseAllocationData =()=>{
    return useMutation(async(body:any)=>{
      return await SupplierWiseAllocation.getSupplierWiseAllocationData(body)
    })
  }

  // export const useGetBOROARemarkHistory = () => {
  //   return useMutation(async (payload:BORDataPayload) => {
  //     return await BORColorBandWiseService.getBOROARemarkHistory(payload);
  //   });
  // }

  // export const useSubmitBOROARemark = () => {
  //   return useMutation(async (payload:{data:Array<SubmitBORRemarkPayload>}) => {
  //     return await BORColorBandWiseService.submitBOROARemark(payload);
  //   });
  // }
  