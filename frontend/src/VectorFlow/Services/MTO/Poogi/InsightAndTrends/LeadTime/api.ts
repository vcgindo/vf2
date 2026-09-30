import axios from "axios";

export const getLeadTimeData = async ({graphflag ,page, appliedFilters ,page_size}:any) => {
  if(graphflag){
    return await axios.get(
      process.env.REACT_APP_VF_API_HOST_MTO + `/getLeadTimeData/`,
      {
        headers: {
          "Content-Type": "application/json",
        },
        params: {
          graphflag

        },
      }
    );
  }
  return await axios.put(
    process.env.REACT_APP_VF_API_HOST_MTO + `/getLeadTimeData/`,
    appliedFilters,
    {
      headers: {
        "Content-Type": "application/json",
      },
      params: {
        graphflag,
        page_size,
        page,
      },
    }
  );
};

export const getLeadTimeExcelData = async({body, isExcelExport , report_name} : {body? : any, isExcelExport? : any , report_name?: any}) =>{
  return await axios.put(
    process.env.REACT_APP_VF_API_HOST_MTO + `/getLeadTimeData/`,
    body,
    {
      headers: {
        "Content-Type": "application/json",
      },
      params : {
        export : isExcelExport,
        report_name
      },
      responseType : "blob"
    }
  );
}
