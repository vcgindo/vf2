import {ReactNode, useState} from 'react';
import {
    SCTabArea,
    SCTabHeader,
    SCTabHeaderLeft,
    SCTabButton,
    SCTabBody,
    SCTabContent,
    SCTabTitle
  } from './styles'
import {type MDMMasterState} from '../../../../VectorFlow/types/MDM';
import { useSelector } from 'react-redux';
import { RootState } from "../../../../redux/store/store";
 
interface VFTabProps{
  activeMaster:MDMMasterState,
  themeUi:string,
  onTabChange:(master: MDMMasterState) => void,
  onTabClose:(e:React.MouseEvent<HTMLElement>,master:MDMMasterState) => void,
  newTabTitle?:string | undefined,
  newTabIcon?:string,
  newTabHandler?:() => void,
  children?:ReactNode,
 
}
 
const VFTab = ({activeMaster,themeUi,onTabChange,onTabClose,newTabTitle,newTabIcon,newTabHandler,children}:VFTabProps) => {
 
  const masters = useSelector((state:RootState)=>state.mdm.masters);
 
  const getTabStatus = (currMaster:MDMMasterState) => {
    if(currMaster.progress === 'submitted' || currMaster.progress === 'editOnlineSubmitted' || currMaster.progress === 'deleteOnlineSubmitted') return 'completed';
    return activeMaster.id === currMaster.id ? 'active' : currMaster.progress;
 
  }
 
  const [isHovered, setIsHovered] = useState(false);
 
  const handleMouseEnter = (master:any) => {
   if( getTabStatus(master) === 'active') { setIsHovered(true);}
  };
 
  const handleMouseLeave = () => {
    
    setIsHovered(false);
  };
 
  const getImageSrc = (master: MDMMasterState) => {
    if (isHovered && getTabStatus(master) === 'active') {
      return '/assets/img/VectorFLOW/NMS/close-icon-hover.svg';
    }
    if (getTabStatus(master) === 'active') {
      return '/assets/img/VectorFLOW/NMS/close-icon.svg';
    }
    if (master.progress === 'submitted' || master.progress === 'editOnlineSubmitted'|| master.progress==='deleteOnlineSubmitted') {
      return '/assets/img/VectorFLOW/NMS/tick.svg';
    }
    else{
    return '/assets/img/VectorFLOW/NMS/close.svg';
    }
  };
 
  return(
      <SCTabArea>
        <SCTabHeader>
            <SCTabHeaderLeft>
              {
                masters.map((master:MDMMasterState,index:number)=>{
                  return(
                    <SCTabButton
                      status={getTabStatus(master)}
                      zIndex={masters.length-index}
                      marLeft={index !== 0}
                      themeUi={themeUi}
                      onClick={() => {
                        onTabChange(master)
                      }}
                      key={master.id}
                      data-testid="tab-button"
                      >
                        <SCTabContent>
                          <SCTabTitle status={getTabStatus(master)}>          
                            {master.id == 11 ? 'AbsoluteValueSeasonality' : 
                             master.id == 12 ? 'DeltaPercentageSeasonality' : 
                             master.name}
                          </SCTabTitle>
                          {/* <img data-testid="tab-close" onClick={(e:React.MouseEvent<HTMLElement>) => {onTabClose(e,master)}} src={getTabStatus(master) === 'active' ? "/assets/img/VectorFLOW/NMS/close-white.svg" : (master.progress === 'submitted' || master.progress === 'editOnlineSubmitted') ? "/assets/img/VectorFLOW/NMS/tick.svg" : "/assets/img/VectorFLOW/NMS/close.svg"}/> */}
                          <img
                            data-testid="tab-close"
                            onClick={(e: React.MouseEvent<HTMLElement>)=>{
                              onTabClose(e, master)
                              setIsHovered(false);

                            }}
                            onMouseEnter={() => handleMouseEnter( master)}
                            onMouseLeave={handleMouseLeave}
                            src={getImageSrc(master)}
                            alt="Tab Icon"
                          />
                        </SCTabContent>
                    </SCTabButton>
                  )
                })
              }
              <SCTabButton
                status={''}
                zIndex={0}
                marLeft={true}
                themeUi={themeUi}
                onClick={() => {
                  if(newTabHandler) newTabHandler();
                }}
                data-testid="new-tab"
              >
                  <SCTabContent>
                    <img style={{marginRight:'18px'}} src={newTabIcon}/>
                    <SCTabTitle status={''}>{newTabTitle}</SCTabTitle>
                  </SCTabContent>
              </SCTabButton>
            </SCTabHeaderLeft>
 
        </SCTabHeader>
        <SCTabBody>
          {children}
        </SCTabBody>
    </SCTabArea>
  )
}
 
export default VFTab;