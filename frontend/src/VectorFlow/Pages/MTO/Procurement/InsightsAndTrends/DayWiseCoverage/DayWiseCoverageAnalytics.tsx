import React from 'react'
import { useSelector } from 'react-redux'
import { AnalyticsCol, AnalyticsRow, AnalyticsTable } from './style'

const DaywiseCoverageAnalytics = () => {

  const data = useSelector((state: any) => state.mto.DaywiseCoverageAnalytics)

  console.log(data);
  if(!data){
    return <></>
  }
  
  return (
    <AnalyticsTable>
      <thead>
        <AnalyticsRow>
          <AnalyticsCol>Analytics</AnalyticsCol>
        </AnalyticsRow>
        <AnalyticsRow>
          <AnalyticsCol>Months</AnalyticsCol>
          <AnalyticsCol>No of Green</AnalyticsCol>
          <AnalyticsCol>No of Red</AnalyticsCol>
          <AnalyticsCol>% of Green</AnalyticsCol>
        </AnalyticsRow>
      </thead>
      <tbody>
      {data.map((row: any, index: number)=>{
        return ( <AnalyticsRow key={index}>
          <AnalyticsCol>{row[0]}</AnalyticsCol>
          <AnalyticsCol>{row[1]}</AnalyticsCol>
          <AnalyticsCol>{row[2]}</AnalyticsCol>
          <AnalyticsCol>{row[3]}%</AnalyticsCol>
        </AnalyticsRow>)
      })}
      {/* <AnalyticsRow>
          <AnalyticsCol>Jun</AnalyticsCol>
          <AnalyticsCol>10</AnalyticsCol>
          <AnalyticsCol>10</AnalyticsCol>
          <AnalyticsCol>50%</AnalyticsCol>
        </AnalyticsRow>
        <AnalyticsRow>
          <AnalyticsCol>Jul</AnalyticsCol>
          <AnalyticsCol>10</AnalyticsCol>
          <AnalyticsCol>0</AnalyticsCol>
          <AnalyticsCol>100%</AnalyticsCol>
        </AnalyticsRow>
        <AnalyticsRow>
          <AnalyticsCol>Aug</AnalyticsCol>
          <AnalyticsCol>10</AnalyticsCol>
          <AnalyticsCol>10</AnalyticsCol>
          <AnalyticsCol>50%</AnalyticsCol>
        </AnalyticsRow> */}
      </tbody>
    </AnalyticsTable>
  )
}

export default DaywiseCoverageAnalytics