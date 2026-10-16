import axios from 'axios';
import { formatFilterJSON, getBodyForExcelExport } from '../../../../../helpers/utils';
import { pagination } from '../../../../../VectorFlow/Pages/MTO/Common/Enum';

type OverallBMReportInputType = {
    page?: number,
    appliedFilters?: any,
    page_size?: number,
    analytics?: 0 | 1,
    user?: any,
    isBomExplosion?: any,
    headersdata?:any,
    colDefMap?: any,
    isExcelExport?: any,
    body?: any,
    report_name?:any,
}

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace OverallBMReportService {

    export const getOverallBMReportData = async ({ body,page, appliedFilters, page_size, analytics = 0,isBomExplosion,isExcelExport = false, report_name }: OverallBMReportInputType) => {
        const finalPageSize = page_size || Number(process.env.REACT_APP_MTO_BM_REPORT_ROWS_PER_PAGE) || pagination.mtoPageSize;
        if (isExcelExport) {
                return await axios.put(
                    process.env.REACT_APP_VF_API_HOST_MTO + `/getOverAllBMReportData/?avawip=${0}&report_name=${report_name}&page=${page}&page_size=${finalPageSize}&analytics=${analytics}`,
                    body,
                    {
                        headers: { 'Content-Type': 'application/json' },
                        params : {
                            // report_name,
                            export : isExcelExport,
                            isBomExplosion:isBomExplosion,
                        },
                        responseType : 'blob'
                    });
                }
            
              const requestBody = {
                ...appliedFilters,
              };
        if (analytics == 0) {
            return await axios.put(
                process.env.REACT_APP_VF_API_HOST_MTO + `/getOverAllBMReportData/?avawip=${0}&page=${page}&page_size=${finalPageSize}&analytics=${analytics}`,
                requestBody, // Pass the modified body
                {
                    headers: {
                        'Content-Type': 'application/json',
                    }
                }
            );
        } else {

            return await axios.put(
                process.env.REACT_APP_VF_API_HOST_MTO + `/getDeptWiseBMReportData/?avawip=${0}&analytics=${analytics}`,
                requestBody, // Pass the modified body
                {
                    headers: {
                        'Content-Type': 'application/json',
                    }
                }
            );
        }
    }

    export const shortOrder_completeOrder =async (body:any) => {

        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + "/updateBMReportOrders/",body,{
        headers: {
            'Content-Type': 'application/json',
            //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
        }})
        
        
    }
}
