import axios from 'axios';
import { pagination } from '../../../../../VectorFlow/Pages/MTO/Common/Enum';


// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace OrderwiseCoverageService {
    export const getOrderwiseCoverageData = async ({page, graph, appliedFilters,page_size}: { page?: number, graph: number, appliedFilters?: any,page_size?:any }) => {

        if(graph){
            return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getRMPMCoverageData/`, {
                headers: {
                    'Content-Type': 'application/json',
                    //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
                },
                params: {
                    graphflag: graph
                }
            })
        }
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getRMPMCoverageData/`, 
        appliedFilters,
        {
    
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
            params: {
                page,
                graphflag: graph,
                page_size: page_size || pagination.mtoPageSize

            }
        })
    }

    export const getOrderwiseCoverageDataForExcelExport = async ({body, isExcelExport , report_name, graph  }: { body: any , isExcelExport : any , report_name : any, graph : number }) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getRMPMCoverageData/`,body, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
            params: {
                export : isExcelExport ,
                report_name,
                graph
            },
            responseType: 'blob'
        })
    }

}
