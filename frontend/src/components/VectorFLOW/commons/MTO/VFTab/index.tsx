import {ReactNode} from 'react';
import {
    SCTabArea,
    SCTabHeader,
    SCTabHeaderLeft,
    SCTabButton,
    SCTabBody,
    SCTabContent,
    SCTabTitle
  } from './styles'
import {type MDMMasterState} from '../../../../../VectorFlow/types/MDM';
import { useSelector } from 'react-redux';
import { RootState } from "../../../../../redux/store/store";

interface VFTabProps{
  activeMaster:MDMMasterState,
  themeUi:string,
  onTabChange:(master: MDMMasterState) => void,
  onTabClose:(e:React.MouseEvent<HTMLElement>,master:MDMMasterState) => void,
  newTabTitle?:string | undefined,
  newTabIcon?:string,
  newTabHandler?:() => void,
  children?:ReactNode,
  isAdd?: boolean

}

const VFTab = ({activeMaster,themeUi,onTabChange,onTabClose,newTabTitle,newTabIcon,newTabHandler,children, isAdd}:VFTabProps) => {

  const masters = useSelector((state:RootState)=>state.mdm.masters);

  const getTabStatus = (currMaster:MDMMasterState) => {
    if(currMaster.progress === 'submitted' || currMaster.progress === 'editOnlineSubmitted') return 'completed';
    return activeMaster.id === currMaster.id ? 'active' : currMaster.progress;

  }

  const finMasters:any = isAdd? [masters[0]]: masters;

  return(
      <SCTabArea>
        <SCTabHeader style={{zoom: 0.8}}>
            <SCTabHeaderLeft>
              {
                finMasters.map((master:MDMMasterState,index:number)=>{
                  return(
                    <SCTabButton 
                      status={getTabStatus(master)} 
                      zIndex={masters.length-index} 
                      marLeft={index !== 0} 
                      themeUi={themeUi}
                      // onClick={() => { 
                      //   onTabChange(master) 
                      // }}
                      key={master.id}
                      data-testid="tab-button"
                      >
                        <SCTabContent>
                          <SCTabTitle status={getTabStatus(master)}>{master.name}</SCTabTitle>
                         
                        </SCTabContent>
                    </SCTabButton>
                  )
                })
              }
             
            </SCTabHeaderLeft>

        </SCTabHeader>
        <SCTabBody>
          {children}
        </SCTabBody>
    </SCTabArea>
  )
}

export default VFTab;