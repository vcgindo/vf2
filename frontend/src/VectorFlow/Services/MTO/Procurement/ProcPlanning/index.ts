import { useMutation } from '@tanstack/react-query'

import { ProcPlanningService } from './api'

export const QUERY_KEYS = {
    userGetProcPlanningData: ['ProcPlanningService.userGetProcPlanningData'],
    userGetProcAfterSimulationPlanningData: ['ProcPlanningService.userGetProcAfterSimulationPlanningData'],
    UpdateBatchWiseCompAllSimulation: ['ProcPlanningService.UpdateBatchWiseCompAllSimulation']
}
export const userGetProcPlanningData = () => {
    return useMutation(async (data: { date: string, pageNum: string, ca: string, appliedFilters: any, page_size?:any }) => {
        return await ProcPlanningService.GetProcPlanningData(data.date, data.pageNum, data.ca, data.appliedFilters, data.page_size);
    });
}

export const userGetProcAfterSimulationPlanningData = () => {
    return useMutation(async (props: {date: string, eas: string, pageNumber: string}) => {
        return await ProcPlanningService.GetProcDataAfterSimulation(props.date, props.eas, props.pageNumber);
    });
}

export const UpdateBatchWiseCompAllSimulation = () => {
    return useMutation(async (body: any) => {
        return await ProcPlanningService.UpdateBatchWiseCompAllSimulation(body)
    })
}

export const putUpdateProcurementSimulationData = () => {
    return useMutation(async (body: any) => {
        return await ProcPlanningService.UpdateProcurementSimulationData(body);
    })
}

export const useGetProcurementPlanningDataForExcelExport = () => {
    return useMutation(async (params: any) => {
        return await ProcPlanningService.GetProcPlanningDataForExcelData(params);
    })
}

export const useGetProcAfterSimulationPlanningDataForExcelExport = () => {
    return useMutation(async (params: any) => {
        return await ProcPlanningService.GetProcDataAfterSimulationForExcelData(params);
    })
}


