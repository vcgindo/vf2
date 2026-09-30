import axios from 'axios';
import { pagination } from '../../../../../../VectorFlow/Pages/MTO/Common/Enum';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace STPLAndFullKitService {

    export const getSTPLandFullkitInDaysData = async ({ graphflag, page, appliedFilters,page_size }: { graphflag: number, page?: number, appliedFilters?: any,page_size?:any  }) => {
        if(graphflag){
            return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getSTPLandFullkitInDaysData/?graphflag=${graphflag}`, 
            {
                headers: {
                    'Content-Type': 'application/json',
                },
            })
        }
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getSTPLandFullkitInDaysData/?graphflag=${graphflag}&page=${page}&page_size=${page_size || pagination.mtoPageSize}`, 
        appliedFilters,
        {
            headers: {
                'Content-Type': 'application/json',
            },
        })
    }

    export const getSTPLandFullkitInDaysExcelData = async ({ graphflag, body, isExcelExport,report_name }: { graphflag: number, body? : any, isExcelExport?: any,report_name : any  }) => {
        
            return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getSTPLandFullkitInDaysData/?graphflag=${graphflag}&export=${isExcelExport}&report_name=${report_name}`,body, 
            {
                headers:{
                    'Content-Type': 'application/json',
                },
                responseType : "blob"

            }
            )
        
    }

}
