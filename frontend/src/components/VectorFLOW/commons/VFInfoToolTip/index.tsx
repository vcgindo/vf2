import {useState} from 'react'
import Portal from '../../layouts/Portal'
import { Icon, TextWrapper, Wrapper,Text } from "./styles"


interface VFInfoToolTipProps{
    infoList:Array<string>
}

interface ToolTipPositionType{
    top:number
    left:number
}

const VFInfoToolTip = (props:VFInfoToolTipProps)=>{

    const {
        infoList
    } = props



    const [isOpen,setIsOpen] = useState<boolean>(false)
    const [tooltipPosition,setTooltipPosition] = useState<ToolTipPositionType>({
        top:0,
        left:0
    })
    
    const onOpenToolTip = (e:React.MouseEvent<HTMLElement>)=>{
        const rect = e.currentTarget.getBoundingClientRect();
        setTooltipPosition({
            top: window.scrollY + rect.top +120,
            left: window.scrollX + rect.left - 90
            
        });

        setIsOpen(true)
    }

    return(
        <Wrapper  >
            {isOpen?<Icon src={"/assets/img/VectorFLOW/BPR/cancel.svg"} onClick={()=>setIsOpen(false)}/>:<Icon src={"/assets/img/VectorFLOW/BPR/info.svg"} onClick={onOpenToolTip}/>}
            {isOpen &&  (
                <Portal  wrapperId='tooltip'>
                    <TextWrapper
                        style={{
                            position: 'absolute',
                            top: tooltipPosition.top,
                            left: tooltipPosition.left
                        }}
                        >

                        {infoList.map(((s,index)=>{
                            return(
                                <Text key={index}>{s}</Text>
                            )
                        }))}
                    </TextWrapper>
                </Portal>
            )}
        </Wrapper>
    )
}

export default VFInfoToolTip