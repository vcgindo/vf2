import axios from 'axios';
import { pagination } from '../../../../../VectorFlow/Pages/MTO/Common/Enum';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace DynamicReleaseManagementService {
    export const getDynamicReleaseData = async ({ graph = 0, ao = 0, page = 1, appliedFilters, page_size, wipObj }: { graph: number, ao: number, page: number, appliedFilters: any, page_size?:any , wipObj?: any}) => {
        // if (graph === 0 && ao === 0 && page === 1) {
        //     return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getDynamicReleaseData/?graph=${graph}&ao=${ao}&page=${page}`, 
        //     appliedFilters,
        //     {
        //         headers: {
        //             'Content-Type': 'application/json',
        //         }
        //     })
        // }

        // else if (ao === 0 && graph !== 0 && page !== 1) {
        //     return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getDynamicReleaseData/?graph=${graph}&ao=${ao}&page=${page}`, 
        //     appliedFilters,
        //     {
        //         headers: {
        //             'Content-Type': 'application/json',
        //         }
        //     })
        // }

        // else if (page === 1 && graph !== 0 && ao !== 0) {
        //     return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getDynamicReleaseData/?graph=${graph}&ao=${ao}&page=${page}`, 
        //     appliedFilters,
        //     {
        //         headers: {
        //             'Content-Type': 'application/json',
        //         }
        //     })
        // }
        // else if (page !== 1 && graph === 0 && ao !== 0) {
        //     return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getDynamicReleaseData/?graph=${graph}&ao=${ao}&page=${page}`, 
        //     appliedFilters,
        //     {
        //         headers: {
        //             'Content-Type': 'application/json',
        //         }
        //     })
        // }
        // else if (page === 1 && graph === 0 && ao !== 0) {
        //     return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getDynamicReleaseData/?graph=${graph}&ao=${ao}&page=${page}`,
        //     appliedFilters,
        //     {
        //         headers: {
        //             'Content-Type': 'application/json',
        //         }
        //     })
        // }
        // else if (page === 1 && graph !== 0 && ao === 0) {
        //     return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getDynamicReleaseData/?graph=${graph}&ao=${ao}&page=${page}`, 
        //     appliedFilters,
        //     {
        //         headers: {
        //             'Content-Type': 'application/json',
        //         }
        //     })
        // }

        // else if (page !== 1 && graph !== 0 && ao !== 0) {
        //     return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getDynamicReleaseData/?graph=${graph}&ao=${ao}&page=${page}`, 
        //     appliedFilters,
        //     {
        //         headers: {
        //             'Content-Type': 'application/json',
        //         }
        //     })
        // }

        if(wipObj){
            return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getDynamicReleaseData/?graph=${graph}&ao=${ao}&page=${page}&page_size=${page_size || pagination.mtoPageSize}`, 
                {...appliedFilters, wip : wipObj},
                {
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
        }

        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getDynamicReleaseData/?graph=${graph}&ao=${ao}&page=${page}&page_size=${page_size || pagination.mtoPageSize}`, 
        appliedFilters,
        {
            headers: {
                'Content-Type': 'application/json',
            }
        })


    }

    export const saveRouteData = async (params: any) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/updateOrderDataRoute/`, params.body, {
            headers: {
                'Content-Type': 'application/json',
            },
            params : {
                update_order_wip : params.update_order_wip
            }
        })
    }

    export const updateDynamicReleaseData = async (body: any) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/UpdateDynamicReleaseData/`, body, {
            headers: {
                'Content-Type': 'application/json',
            }
        })
    }

    export const getDynamicReleaseExcelData = async ({body, isExcelExport , report_name , ao ,graph}: {body : any,isExcelExport : any, report_name : any,ao : any , graph : any}) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getDynamicReleaseData/?graph=${graph}&ao=${ao}&report_name=${report_name}&export=${isExcelExport}`, body, {
            headers: {
                'Content-Type': 'application/json',
            },
            responseType : "blob"
        })
    }

    export const FetchFOLGap = async (params: any) => {
        return await axios.post(process.env.REACT_APP_VF_API_HOST_MTO + `/GetFOLBasedDueDate/`, params.body, {
            headers: {
                'Content-Type': 'application/json',
            },
        })
    }
}
