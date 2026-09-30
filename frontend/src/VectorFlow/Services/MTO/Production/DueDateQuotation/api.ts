import axios from 'axios';
import { pagination } from '../../../../../VectorFlow/Pages/MTO/Common/Enum';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace DueDateQuotationService {
    export const getUIConfig = async (reportName: string) => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getUIReportConfiguration/`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
            params: {
                reportName: reportName
            }
        })
    }

    export const getFilteredOrdersForDDQ = async ({page, unSch, appliedFilters, page_size}: any) => {
       
        if(appliedFilters && Object.keys(appliedFilters).length){
            return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getOrdersForDDQ/?page=${page}&unSch=${unSch ? 1 : 0}&page_size=${page_size || pagination.mtoPageSize}`,
            appliedFilters,
            {
                headers: {
                    'Content-Type': 'application/json',
                    //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
                }
            },
            )
        }
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getOrdersForDDQ/?page=${page}&unSch=${unSch ? 1 : 0}&page_size=${page_size || pagination.mtoPageSize}`,{
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            }
        })

    }

    export const getDDQAnalyticsData = async () => {
       
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getOrdersForDDQ/?analytics=1`,{
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            }
        })
    }

    export const getBufferMasterData = async () => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getBufferMasterData/`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
        })
    }

    export const getCCRGroupMaster = async () => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getCCRGroupMasterData/`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
        })
    }

    export const getRouteDetails = async (route_id: number) => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getRouteDetails/`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
            params: {
                r_id: route_id
            }
        })
    }

    export const getCCRItemTypeMappingMaster = async () => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getCCRItemTypeMapping/`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
        })
    }

    export const getFOLData = async () => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getFOLData/`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
        })
    }

    export const getCCRMasterData = async () => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getCCRMasterData/`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
        })
    }

    export const getDailyWorkingCalendar = async () => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getDailyWorkingCalendar/`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
        })
    }

    export const getMarketOperatingLeadTimeMasterData = async () => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getMarketOperatingLeadTimeMasterData/`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
        })
    }


    export const getLineCCRDetails = async (body: string[]) => {
        return await axios.post(process.env.REACT_APP_VF_API_HOST_MTO + `/getLineCCRDetailsData/`, body, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
        })
    }

    export const updateBuffRouteCCREstDate = async (body: { bufferData: any, routeData: any }) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/UpdateBuffRouteCCREstDate/`, body, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
        })
    }

    export const updateScheduleOrders = async (body: { orders: any }) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/updateScheduleOrders/`, body, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
        })
    }

    export const getFilteredOrdersForExcelDDQ = async ({ body, isExcelExport, report_name, unSch, isBomExplosion }: any) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getOrdersForDDQ/?export=${isExcelExport}&report_name=${report_name}&unSch=${unSch ? 1 : 0}&isBomExplosion=${isBomExplosion}`
            ,body,{
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
            responseType : "blob"
        })

    }

}
