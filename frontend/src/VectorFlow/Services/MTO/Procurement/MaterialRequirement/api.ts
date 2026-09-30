import axios from 'axios';
import { pagination } from '../../../../../VectorFlow/Pages/MTO/Common/Enum';


// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace MaterialRequirementService {
    export const getMaterialRequirementData = async ({currPage, releaseDate, appliedFilters,body,isExcelExport = false, report_name, page_size}: any) => {
        if(isExcelExport) {
            return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getMaterialRequirementData/?releaseDate=${releaseDate}&page_size=${page_size || pagination.mtoPageSize}`, 
            body,
            {
    
                headers: {
                    'Content-Type': 'application/json',
                    //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
                },
                params: {
                    export : isExcelExport,
                    report_name
                },
                responseType: 'blob' 
            })  
        }
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getMaterialRequirementData/?page=${currPage}&releaseDate=${releaseDate}&page_size=${page_size || pagination.mtoPageSize}`, 
        appliedFilters,
        {

            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            }
        })
    }

    export const getMaterialRequirementDataDayWise = async ({currPage, releaseDate, appliedFilters ,body , isExcelExport = false ,report_name,page_size}: any) => {
        if(isExcelExport){
            return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getMaterialRequirementDayWiseData/?releaseDate=${releaseDate}`, 
            body,
            {
                headers: {
                    'Content-Type': 'application/json',
                    //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
                },
                params: {
                    export : isExcelExport,
                    report_name
                },
                responseType: 'blob'  // 'blob' for downloading the file as a blob instead of text
            })    
        }
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getMaterialRequirementDayWiseData/?page=${currPage}&releaseDate=${releaseDate}&&page_size=${page_size || pagination.mtoPageSize}`, 
        appliedFilters,
        {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            }
        })

    }

    // export const getLastRunDate=async()=>{
    //     return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getRunDate/`, {
    //         headers: {
    //             'Content-Type': 'application/json',
    //             //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
    //         }
    //     })
    // }

}
