import axios from 'axios';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace OTAndIFAanalysisService {

    export const getOTAndIFAnalysisData = async ({graphflag, page, appliedFilters,page_size}: any) => {
        if(graphflag){
            return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getOTandIFAnalysisData/`, {
                headers: {
                    'Content-Type': 'application/json',
                },
                params:{
                    graphflag,
                }
            })
        }
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getOTandIFAnalysisData/`, 
        appliedFilters,
        {
            headers: {
                'Content-Type': 'application/json',
            },
            params:{
                graphflag,
                page,
                page_size
            }
        })

    }

    export const getOTAndIFAnalysisDataExcelExport = async ({graphflag, body, report_name,isExcelExport}: any) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getOTandIFAnalysisData/`, 
        body,
        {
            headers: {
                'Content-Type': 'application/json',
            },
            params:{
                graphflag,
                report_name,
                export : isExcelExport
            },
            responseType : 'blob'
        })
    }
}
