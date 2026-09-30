/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios';

export namespace OrderAtRiskService {

   

    export const getOrderAtRiskData = async ({ page, appliedFilters, page_size, graphflag }: any) => {
        if (graphflag) {
          return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getOrdersAtRiskData/`, {
            headers: {
              'Content-Type': 'application/json',
            },
            params: {
              graphflag,
            },
          });
        }
      
        return await axios.put(
          process.env.REACT_APP_VF_API_HOST_MTO + `/getOrdersAtRiskData/`,
          appliedFilters, 
          {
            headers: { 'Content-Type': 'application/json' },
            params: {
              page,
              page_size,
              graphflag, 
            },
          }
        );
      };
      

       
 

    export const getOrderAtRiskDataExcelExport = async ({ body, isExcelExport, report_name,graphflag}: any) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getOrdersAtRiskData/`,
        body,
        {
            headers: { 'Content-Type': 'application/json' },
            params: {
                export : isExcelExport,
                report_name,
                graphflag

            },
            responseType: 'blob' 
        });
    }
}