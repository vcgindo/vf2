import axios from "axios";

export const getRunState = async () => {
  return await axios.get(
    process.env.REACT_APP_VF_API_HOST_MTO + `/getLatestRunStatus/`,
    {
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
};

export const getFileConfiguration = async () => {
  return await axios.get(
    process.env.REACT_APP_VF_API_HOST_MTO + `/getFileConfiguration/?client_id=1`,
    {
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
};


export const getFileDownload = async (file_name: string) => {
  return await axios.get(
    process.env.REACT_APP_VF_API_HOST_MTO + `/getSchedularFileOnDownload/?file_name=${file_name}`,
    {
      headers: {
        "Content-Type": "application/json",
      },
      responseType: 'blob'
    }
  );
}

export const postUploadSchedulerFile = async (formData: FormData) => {
  console.log("formData", formData);
  return await axios.post(
    process.env.REACT_APP_VF_API_HOST_MTO + `/SaveSchedulerInputFileOnUpload/`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );
}

export const postStartSchedulingRun = async (userdata: {user_id: string, user_name: string}) => {
  return await axios.post(
    process.env.REACT_APP_VF_API_HOST_MTO + `/startSchedulerRun/`,
    userdata
    ,
    {
      headers: {
        "Content-Type": "application/json",
      },
    }
  )
}

export const getFinalResultData = async ()=>{
  return await axios.get(
    process.env.REACT_APP_VF_API_HOST_MTO + `/getSchedulerRunResultJson/`,
    {
      headers: {
        "Content-Type": "application/json",
      },
    }
  )
}