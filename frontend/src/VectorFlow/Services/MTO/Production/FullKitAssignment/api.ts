import axios from 'axios';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace FullKitAssignmentService {
    export const getFullKitAssignmentDataWithGraphData = async (is_fullkit: boolean, load_data_after_simulation: boolean, load_graph_data: boolean, page: number, pageSize: number, appliedFilters: any) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getFullKitAssignmentDataWithGraphData/`, 
        appliedFilters,
        {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
            params:{
                is_fullkit,
                load_data_after_simulation,
                load_graph_data,
                page,
                page_size: pageSize
            }
        })
    }

    export const updateExcludedOrdersForFullkitAssignment = async (orders: any, username: string) => {
        return await axios.post(process.env.REACT_APP_VF_API_HOST_MTO + `/updateExcludedOrdersForFullkitAssignment/`, {orders, username} ,{
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            }
        })
    }
    
    export const updateOrSimulateStockAllocation = async (is_simulated: boolean, username: string) => {
        return await axios.post(process.env.REACT_APP_VF_API_HOST_MTO + `/UpdateOrSimulateStockAllocation/`, null,{
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
             params: {
                username,
                is_simulated, 
             }
        })
    }

    export const updateFullkitOnSimulation = async (is_type: string, username: string) => {
        return await axios.post(process.env.REACT_APP_VF_API_HOST_MTO + `/UpdateFullkitOnSimulation/`, null,{
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
             params: {
                username,
                is_type, 
             }
        })
    }
    export const getFullKitAssignmentDataWithGraphExcelData = async ({is_fullkit , load_data_after_simulation , load_graph_data , body,isExcelExport ,report_name}:{is_fullkit: boolean, load_data_after_simulation: boolean, load_graph_data: boolean, body : any , isExcelExport : any , report_name : any}) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getFullKitAssignmentDataWithGraphData/`, 
        body,
        {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
            params:{
                is_fullkit,
                load_data_after_simulation,
                load_graph_data,
                export : isExcelExport,
                report_name
            },
            responseType : "blob"
        })
    }
    
}
