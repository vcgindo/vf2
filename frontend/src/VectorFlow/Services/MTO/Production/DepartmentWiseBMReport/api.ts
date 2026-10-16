import axios from 'axios';
import { pagination } from '../../../../../VectorFlow/Pages/MTO/Common/Enum';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace DepartmentWiseBMReport {

    export const getFilteredDeptWiseBMReport = async ({ wip, curr, appliedFilters, page_size, isBomExplosion, isExcelExport = false,body,page, report_name }: any) => {
        if (isExcelExport) {
            return await axios.put(
                process.env.REACT_APP_VF_API_HOST_MTO + `/getDeptWiseBMReportData/?avawip=${wip}&report_name=${report_name}`,
                body,
                {
                    headers: { 'Content-Type': 'application/json' },
                    params : {
                        export : isExcelExport,
                        isBomExplosion:isBomExplosion,
                    },
                    responseType : 'blob'
                });
            }
        
          const requestBody = {
            ...appliedFilters,
          };
        const finalPageSize = page_size || Number(process.env.REACT_APP_MTO_BM_REPORT_ROWS_PER_PAGE) || pagination.mtoPageSize;
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getDeptWiseBMReportData/?avawip=${wip}&page=${curr}&page_size=${finalPageSize}`,
            appliedFilters,
            {
                headers: {
                    'Content-Type': 'application/json',
                    //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
                }
            },
        )

    }

    export const getBombLevelData = async (data: any) => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getBOMLevelWiseAllocationData/?oid=${data.oid}&lid=${data.lid}`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            }
        })
    }

    export const addBMReportRemark = async (body: any) => {
        //console.log('addAPI Call',body)
        return await axios.post(process.env.REACT_APP_VF_API_HOST_MTO + `/createBMReportRemarksData/`, body, {
            headers: { 'Content-Type': 'application/json' }
        })
    }

    export const getDeptWiseWipData = async (body: any) => {
        return await axios.post(process.env.REACT_APP_VF_API_HOST_MTO + `/getDeptWiseWipData/`, body, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            }
        })
    }

    export const getHighAgeingData = async (body: any) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getHighAgeingData/`, body, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            }
        })
    }
}
