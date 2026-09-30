import { useMutation, } from '@tanstack/react-query'
import { getElapsedDaysforDeptPlantData, getElapsedTimeData } from './api';


export const useGetElapsedTimeData = () => {
    return useMutation(async (params: {graphflag: any, page?: number, appliedFilters?: any, page_size?:any}) => {
        return getElapsedTimeData(params);
    })
}


export const useGetElapsedDaysforDeptPlantData = () => {
    return useMutation(async (data: {plant: number, dept: number}) => {
        return getElapsedDaysforDeptPlantData(data.plant, data?.dept);
    })
}

export const useGetElapsedTimeDataForExcelExport = () => {
    return useMutation(async (params : any) => {
        return getElapsedTimeData(params);
    })
}


