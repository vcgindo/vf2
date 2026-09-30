/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios';

export namespace MaterialCoverageServices {


    // console.log('url',process.env.REACT_APP_VF_API_HOST_MTO + `/getOpenSOSummaryData/`)
    export const getMaterialSOData = async () => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getOpenSOSummaryData/`,
        {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            }
        })
    }

    export const getOpenSODetailsData=async({data,appliedFilters}:any)=>{
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getOpenSODetailsData/${data}`,
            appliedFilters,
             {
            headers: { 
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            }
        })
    }

    export const getOpenSODetailsDataForExcelExport =async ({data , body , isExcelExport, report_name, isChildren} : {data : string , body : any , isExcelExport : number , report_name : string,isChildren:any} ) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getOpenSODetailsData/${data}`, body,{
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
            params : {
                export : isExcelExport,
                report_name,
                isChildren
            },
            responseType : 'blob'
        })    
    }


}