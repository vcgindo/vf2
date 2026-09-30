import { useMutation, } from '@tanstack/react-query'
import { getLeadTimeData,getLeadTimeExcelData } from './api';

export const useGetLeadTimeData = () => {
    return useMutation(async (data:any) => {
        return getLeadTimeData(data);
    })
}

export const useGetLeadTimeExcelData = () => {
    return useMutation(async (params : any) => {
        return getLeadTimeExcelData(params);
    })
}