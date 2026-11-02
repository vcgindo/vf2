
import {useEffect, useRef, useState} from 'react'
import { useGetLastRunDate } from "../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR"
import { UPDATE_LAST_RUN_DATE } from '../redux/actions/MTA'
import { useDispatch } from 'react-redux'
import { isMtaReportCurrent, subscribeMtaReportRefresh } from '../config/mta-publication-binding'


const useGetlastRunData = (providedDate?:string)=>{
   const dispatch = useDispatch();
    const {mutateAsync:getLastRunDate} = useGetLastRunDate()
    const readDate = useRef(getLastRunDate)
    readDate.current = getLastRunDate

    const [lastRunDate,setLastRunDate] = useState<string >("Loading")

   useEffect(()=>{
        if (providedDate !== undefined) return;
        let active = true;
        let sequence = 0;
        const load = async()=>{
            const request = ++sequence;
            setLastRunDate('Loading');
            try{
                const response = await readDate.current()
                if (!active || request !== sequence || !isMtaReportCurrent(response)) return;
                const {data} = response;
                setLastRunDate(data?.data[0].formatted)
                dispatch(UPDATE_LAST_RUN_DATE(data?.data[0].rawDate))
            }catch(err){
                if (!active || request !== sequence) return;
                console.error(err)
                setLastRunDate('Date Unavailable')
            }
        };
        const unsubscribe = subscribeMtaReportRefresh(() => { void load(); });
        void load();
        return () => { active = false; sequence++; unsubscribe(); };
   },[providedDate])


    return {
        date:providedDate ?? lastRunDate
    }
        
}

export default useGetlastRunData