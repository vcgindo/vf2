
import TechnicalWise  from '../TechnicalView'
import EconomicalWise from '../EconomicalView'
import { BufferTrendsGraphState } from '../../../../../types/BPR'
import { useUserData } from '../../../../../../context'

interface ChartViewProps {

  currentTab:string,
  currentGraphData:any,
  currentPageTab:string,
  onFloatingTabChangeOnPages?:(i:any)=>void  
  isLoading:boolean
  graphs:BufferTrendsGraphState[]
  updateGraphState:(id:number, property:string, value:any)=>void
  setHorizondays:any
  handleSubmitClick:()=>void
  horizonDays:number

}

const ChartView = ({currentTab,currentGraphData,currentPageTab,onFloatingTabChangeOnPages,isLoading,graphs,
           updateGraphState,setHorizondays,handleSubmitClick,horizonDays}:ChartViewProps) => {

  const {user} = useUserData()
  const themeUi = user.user.theme_ui

 const renderGraphs = () =>{

  if(currentTab=="tech"){
    return (
    <TechnicalWise
      data={currentGraphData ? currentGraphData:[]}
      currentPageTab={currentPageTab}
      handleClick={onFloatingTabChangeOnPages}
      isLoading={isLoading}
      graphs={graphs}
      updateGraphState={updateGraphState}
      setHorizondays={setHorizondays}
      handleSubmitClick={handleSubmitClick}
      horizonDays={horizonDays}
      themeUi={themeUi}
    />)
  }

  
  if(currentTab=="eco"){
    return (
      <EconomicalWise
        data={currentGraphData ? currentGraphData:[]}
        currentPageTab={currentPageTab}
        handleClick={onFloatingTabChangeOnPages}
        isLoading={isLoading}
        graphs={graphs}
        updateGraphState={updateGraphState}
        setHorizondays={setHorizondays}
        handleSubmitClick={handleSubmitClick}
        horizonDays={horizonDays}
        themeUi={themeUi}
    />
    )
  }
 }
    
  return (
    <>
       {renderGraphs()}
    </>

  )   
}

export default ChartView