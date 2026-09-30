import { useMutation } from '@tanstack/react-query'

import { MCGridService } from './api'


export const QUERY_KEYS = {

}
 


export const useGetGridHealth = () => {
return useMutation(async (payload:any) => {
    return await MCGridService.getGridHealth(payload);
});
}

