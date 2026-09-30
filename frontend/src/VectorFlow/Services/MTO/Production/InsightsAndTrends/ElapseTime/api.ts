import axios from "axios";
import { pagination } from '../../../../../../VectorFlow/Pages/MTO/Common/Enum';


export const getElapsedTimeData = async ({ graphflag, page, appliedFilters, isExcelExport = false, body, report_name, page_size }: { graphflag: number, page?: number, appliedFilters?: any, isExcelExport?: any, body?: any, report_name?: any, page_size?: any }) => {
  const finalPageSize = page_size || pagination.mtoPageSize;
  if(isExcelExport){
    return await axios.put(
      process.env.REACT_APP_VF_API_HOST_MTO + `/getElapsedTimeData/`,body,{
        headers: {
          "Content-Type": "application/json",
        },
        params: {
          export : isExcelExport,
          report_name
        },
        responseType : 'blob'
      }
    )
  }
  else if(graphflag){
    return await axios.get(
      process.env.REACT_APP_VF_API_HOST_MTO + `/getElapsedTimeData/`,
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
    process.env.REACT_APP_VF_API_HOST_MTO + `/getElapsedTimeData/`,
    appliedFilters,
    {
      headers: {
        "Content-Type": "application/json",
      },
      params: {
        graphflag,
        page,
        page_size:finalPageSize,
      },
    }
  );
};

export const getElapsedDaysforDeptPlantData = async (plant: number, dept: number) => {
  return await axios.get(
    process.env.REACT_APP_VF_API_HOST_MTO + `/getElapsedDaysforDeptPlantData/`,
    {
      headers: {
        "Content-Type": "application/json",
      },
      params: {
        plant,
        dept,
      },
    }
  );
};
