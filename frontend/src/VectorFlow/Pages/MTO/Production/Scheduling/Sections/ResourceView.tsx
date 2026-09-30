import React from 'react'
import ResourceViewChart from '../components/ResourceViewChart'
import ResourceViewSummary from '../components/ResourceViewSummary'
import { ResourceViewWrapper } from '../SchedulingStyles'



const ResourceView = ({ResourceData, setExcelGridRef}: any) => {


  return (
    <ResourceViewWrapper>
      <ResourceViewChart ResourceData={ResourceData}/>
      <ResourceViewSummary ResourceData={ResourceData} setExcelGridRef={setExcelGridRef}/>

    </ResourceViewWrapper>
  )
}

export default ResourceView