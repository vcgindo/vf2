import { useMutation } from '@tanstack/react-query'
// import { BMTrends } from './api'
import { getBMTrendsData } from './api'

export const QUERY_KEYS = {
    useGetBMTrendsData: ['MDMService.useGetBMTrendsData'],
}

// export const useGetBMTrendsData = ()=>{
//     return useQuery(QUERY_KEYS.useGetBMTrendsData,async()=>{
//       return await BMTrends.getBMTrendsData()
//     })
//   }

  
export const useGetBMTrendsData = () => {
    return useMutation(async (data: {plant: number}) => {
        return getBMTrendsData(data.plant);
    })
}