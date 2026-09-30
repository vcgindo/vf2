/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'
import { pagination } from '../../../../../VectorFlow/Pages/MTO/Common/Enum';


export namespace ProcPlanningService {

    export const GetProcPlanningData = async (date: string, pageNum: string, ca: string, appliedFilters: any,page_size?:any) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getProcPlanningData/?releaseDate=${date}&page=${pageNum}&ca=${ca}&&page_size=${page_size || pagination.mtoPageSize}`, 
        appliedFilters,
        {
            headers: { 'Content-Type': 'application/json' }
        });
    }
    export const GetProcDataAfterSimulation = async (date: string, eas: string, pageNumber: string) => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getProdDataAfterSimulation/?releaseDate=${date}&eas=${eas}&page=${pageNumber}&page_size=500`, {
            headers: { 'Content-Type': 'application/json' }
        });
    }
    export const UpdateBatchWiseCompAllSimulation = async (body: any) => {
        return await axios.patch(process.env.REACT_APP_VF_API_HOST_MTO + `/updateBatchwiseCompAllocAtSimulation/`, JSON.stringify(body), {
            headers: { 'Content-Type': 'application/json' }
        });
    }

    export const UpdateProcurementSimulationData = async (body: any) => {
        return await axios.post(process.env.REACT_APP_VF_API_HOST_MTO + `/updateProcurementPlanningSimulatedQty/`, JSON.stringify(body), {
            headers: { 'Content-Type': 'application/json' }
        })
    }

    export const GetProcPlanningDataForExcelData = async ({date, body ,ca , report_name,isExcelExport, isChildren,excel_scope}:{date: string,body : any, ca: string, report_name : any , isExcelExport : any, isChildren: boolean,excel_scope:string }) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getProcPlanningData/?releaseDate=${date}&ca=${ca}`, 
        body,
        {
            headers: { 'Content-Type': 'application/json' },
            params : {
                report_name,
                export: isExcelExport,
                isChildren,
                excel_scope
            },
            responseType : 'blob'
        });
    }

    export const GetProcDataAfterSimulationForExcelData = async ({ date, body, eas, report_name, isExcelExport }: { date: string, body: any, eas: string, report_name: any, isExcelExport: any }) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getProdDataAfterSimulation/?releaseDate=${date}&eas=${eas}`,
            body,
            {
                headers: { 'Content-Type': 'application/json' },
                params: {
                    report_name,
                    export: isExcelExport
                },
                responseType: 'blob'
            });
    }

}


