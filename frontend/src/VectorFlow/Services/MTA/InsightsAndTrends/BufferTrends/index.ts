import { useMutation } from '@tanstack/react-query'
import { BufferTrendsService } from './api'


export const QUERY_KEYS = {
  useGetBufferTrendsGraph: ['BufferTrendsService.getBufferTrendsGraph'],
}


export const useGetBufferTrendsGraph = ()=>{
    return useMutation(async(body:any)=>{
        return await BufferTrendsService.getBufferTrendsGraph(body);
    })
}


