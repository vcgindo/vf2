import React, { useEffect, useState } from 'react'
import { useSelector } from 'react-redux';
import {userGetProcPlanningData } from "../../../../Services/MTO/Procurement/ProcPlanning/index";
import { AnalyticsCol, AnalyticsRow, AnalyticsTable } from '../InsightsAndTrends/DayWiseCoverage/style';


const ProcAnalytics = () => {

    const { mutateAsync: getProcPlanningData } = userGetProcPlanningData()

    const [shortageCount, setShortageCount] = useState(0);
    const [availCount, setAvailCount] = useState(0);

    const data = useSelector((state: any) => state.mto.ProcPlanningAnalytics)
    const appliedFilters = useSelector((state: any) => state.mto.AppliedFilters)
    

    const GetData=async()=>{
        try{

            if(data && data.date){

                const response1 =  await getProcPlanningData({ date: data.date, pageNum: '1', ca: '0', appliedFilters })
                const response2 =  await getProcPlanningData({ date: data.date, pageNum: '1', ca: '1', appliedFilters })

            setShortageCount(response1?.data?.data?.count || 0)
            setAvailCount(response2?.data?.data?.count || 0)
            }

            
        }
        catch(error){
            console.log(error)
        }
    }

    useEffect(()=>{
      if(data && !shortageCount && !availCount){
        GetData();
      }
    },[data.date])
   
    
  return (
    <AnalyticsTable style={{display: 'flex',flexDirection: 'column', justifyContent: 'center'}} >
    <thead>
      <AnalyticsRow>
        <AnalyticsCol style={{display: 'flex', justifyContent: 'center'}}>Analytics</AnalyticsCol>
      </AnalyticsRow>
        <hr/>
    </thead>
    <tbody>
     <AnalyticsRow style={{display: 'flex', justifyContent: 'space-between'}}>
        <AnalyticsCol>Count Of RM in Shortage</AnalyticsCol>
        <AnalyticsCol>{shortageCount}</AnalyticsCol>
       
      </AnalyticsRow>
      <AnalyticsRow style={{display: 'flex', justifyContent: 'space-between'}}>
        <AnalyticsCol>Count Of RM Fully Available</AnalyticsCol>
        <AnalyticsCol>{availCount}</AnalyticsCol>
       
      </AnalyticsRow>
      <hr/>
      <AnalyticsRow style={{background: 'black',display: 'flex', justifyContent: 'space-between'}}>
        <AnalyticsCol>Total</AnalyticsCol>
        <AnalyticsCol>{availCount+ shortageCount}</AnalyticsCol>
       
      </AnalyticsRow>

    
 
    </tbody>
  </AnalyticsTable>
  )
}

export default ProcAnalytics