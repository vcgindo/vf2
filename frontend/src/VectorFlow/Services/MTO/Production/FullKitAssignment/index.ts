import { useMutation } from "@tanstack/react-query"
import { FullKitAssignmentService } from "./api"

export const useGetFullKitAssignmentDataWithGraphData = () => {
    return useMutation(async (data: {is_fullkit: boolean, load_graph_data: boolean, load_data_after_simulation: boolean, page: number, pageSize: number, appliedFilters: any}) => {
        return FullKitAssignmentService.getFullKitAssignmentDataWithGraphData(data.is_fullkit, data.load_data_after_simulation, data.load_graph_data, data.page, data.pageSize, data.appliedFilters);
    })
}


interface IUpdateExcludedOrdersForFullkitAssignment{
    orders: {
        on: string,
        lid: string 
    }[],
    username: string
}

export const useUpdateExcludedOrdersForFullkitAssignment = () => {
    return useMutation(async (data: IUpdateExcludedOrdersForFullkitAssignment) => {
        return FullKitAssignmentService.updateExcludedOrdersForFullkitAssignment(data.orders, data.username);
    })
}

export interface IUpdateOrSimulateStockAllocation{
    username: string,
    is_simulated: boolean
}

export const useUpdateOrSimulateStockAllocation = () => {
    return useMutation(async (data: IUpdateOrSimulateStockAllocation) => {
        return FullKitAssignmentService.updateOrSimulateStockAllocation(data.is_simulated, data.username);
    })
}

export interface IUpdateFullkitOnSimulationParams{
    username: string,
    is_type: "Save" | "Delete"
}

export const useUpdateFullkitOnSimulation = () => {
    return useMutation(async (data: IUpdateFullkitOnSimulationParams) => {
        return FullKitAssignmentService.updateFullkitOnSimulation(data.is_type, data.username);
    })
}

export const useGetFullkitAssignmentExcelData = ()=>{
    return useMutation( async (params : any) =>{
        return FullKitAssignmentService.getFullKitAssignmentDataWithGraphExcelData(params);
    })
}