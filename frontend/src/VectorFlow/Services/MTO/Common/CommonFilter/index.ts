import { useMutation } from '@tanstack/react-query'
import { FilterDataService } from './api'

//useQuery for get 
export const QUERY_KEYS = {
    useGetFilterData: ['MDMService.useGetFilterData'],
}

export const useGetFilterData = ()=>{
    return useMutation(async (params: any) => {
      return await FilterDataService.getFilterData(params)
    })
}



