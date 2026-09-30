import { useMutation, /*useQuery*/ } from '@tanstack/react-query'
import { UserUIConfigService } from './api'


export const useGetState = () => {
    return useMutation(async (reportName: any) => {
        return UserUIConfigService.getState(reportName);
    })
}

export const useSaveState = () => {
  return useMutation(async (payload:{reportname:string,state:string}) => {
    return await UserUIConfigService.saveState(payload);
  });
}

export const useResetState = () => {
  return useMutation(async (payload:any) => {
    return await UserUIConfigService.resetState(payload);
  });
}



