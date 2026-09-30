import { useMutation } from "@tanstack/react-query"
import { getFileConfiguration, getFileDownload, getFinalResultData, getRunState, postStartSchedulingRun, postUploadSchedulerFile } from "./api";

export const useGetRunState = () => {
    return useMutation(async () => {
        return getRunState();
    })
}

export const useGetFileConfiguration = () => {
    return useMutation(async () => {
        return getFileConfiguration();
    })
}

export const useGetFileDownloadForSchedular = () => {
    return useMutation(async (file_name: string) => {
        return getFileDownload(file_name);
    })
}

export const usePostFileUploadForSchedular = () => {
    return useMutation(async (formData: FormData) => {
      return postUploadSchedulerFile(formData);
    })
}

export const usePostStartSchedulingRun = () => {
    return useMutation(async (userdata: {user_id: string, user_name: string}) => {
        return postStartSchedulingRun(userdata);
    })
}

export const useGetFinalRunResult = () => {
    return useMutation(async () => {
        return getFinalResultData();
    })  
}