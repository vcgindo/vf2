
import {useEffect, useState} from 'react'
import { useGetLastRunDate } from "../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR"
import { UPDATE_LAST_RUN_DATE } from '../redux/actions/MTA'
import { useDispatch } from 'react-redux'


const useGetlastRunData = ()=>{
   const dispatch = useDispatch();
    const {mutateAsync:getLastRunDate} = useGetLastRunDate()

    const [lastRunDate,setLastRunDate] = useState<string >("Loading")

   useEffect(()=>{
        (async()=>{
            try{
                const {data} = await getLastRunDate()
                setLastRunDate(data?.data[0].formatted)
                dispatch(UPDATE_LAST_RUN_DATE(data?.data[0].rawDate))
            }catch(err){
                console.error(err)
                setLastRunDate('Date Unavailable')
            }
        })()
   },[])


    return {
        date:lastRunDate
    }
        
}

export default useGetlastRunData