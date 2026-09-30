import axios from 'axios';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace ReasonOrderChangeServices {

    export const getPoogiReasonsAnalyticalData = async () => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getPoogiReasonForDelayedOrdersAnalyticsData/`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            }
        })
    }

    export const getPoogiReasonsDelayedOrder = async (data: {
        wip: number,
        curr: number,
        pageSize?: number,
        appliedFilters?: Record<string, any>
    }) => {
        let queryString = `isAssigned=${data.wip}&page=${data.curr}`;
        
        if (data.pageSize !== undefined) {
            queryString += `&page_size=${data.pageSize}`;
        }
    
        return await axios.put(
            `${process.env.REACT_APP_VF_API_HOST_MTO}/getPoogiReasonForDealyedOrdersData/?${queryString}`,
            data.appliedFilters || {},
            {
                headers: {
                    'Content-Type': 'application/json',
                }
            }
        );
    };  

    export const getPoogIRemarks = async (data: string) => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getBMReportRemarksData/?ok=${data}`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            }
        })
    }

    export const getPoogiMajorMinorReason = async () => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getPoogiReasonMasterData/`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            }
        })
    }

    export const updatePoogiRemarks = async (body: any) => {
        // console.log('api', body)
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/updatePoogiReasonsforOrders/`, body, {
            headers: { 'Content-Type': 'application/json' }
        })
    }

    export const getPoogiReasonsDelayedOrderExcelExport = async (data: any) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getPoogiReasonForDealyedOrdersData/?isAssigned=${data.wip}&export=${data.isExcelExport}&report_name=${data.report_name}`, 
        data.body,
        {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
            responseType : 'blob'
        })
    }
}