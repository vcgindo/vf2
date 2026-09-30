import { useMutation } from '@tanstack/react-query'


import { BORColorBandWiseService } from './api'
import { BORDataPayload, SubmitBORRemarkPayload } from '../../../../../VectorFlow/types/BPR';

export const QUERY_KEYS = {
//   useGetBPRUIConfiguration: ['BPRService.useGetBPRUIConfiguration'],
}



export const useGetBORColorBandWiseRecordCount =()=>{
  return useMutation(async(body:any)=>{
    return await BORColorBandWiseService.getBORColorBandWiseRecordCount(body)
  })
}

export const useGetBORColorBandWisData =()=>{
    return useMutation(async(body:any)=>{
      return await BORColorBandWiseService.getBORColorBandWisData(body)
    })
  }

  export const useGetBOROARemarkHistory = () => {
    return useMutation(async (payload:BORDataPayload) => {
      return await BORColorBandWiseService.getBOROARemarkHistory(payload);
    });
  }

  export const useSubmitBOROARemark = () => {
    return useMutation(async (payload:{data:Array<SubmitBORRemarkPayload>}) => {
      return await BORColorBandWiseService.submitBOROARemark(payload);
    });
  }
  