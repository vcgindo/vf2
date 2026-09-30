import { useState,CSSProperties } from "react";
import { SCContainer,SCErrorToolTipLi, SCErrorToolTipUl, SCToolTipWrapper } from "./styles"
import { ICellRendererParams } from "ag-grid-enterprise"
import Portal from "../../layouts/Portal";
import useViewPort from "../../../../hooks/useViewPort";
import { useUserData } from "../../../../context";

const WarningCell = (props:ICellRendererParams)=>{
    const {user} = useUserData()

    const message = props.data.warning;
    const themeUi = user?.user?.theme_ui

    const {getGridZoom,getScreenZoomValue} = useViewPort()

    const currScreenZoom = getScreenZoomValue()
    const currGridZoom = getGridZoom()


    const [errorCellPosition,setErrorCellPosition] = useState<CSSProperties>()
    const [isToolTipOpen,setIsToolTipOpen] = useState<boolean>(false)

    console.debug(isToolTipOpen)

    const messages = message?.split('.').filter((msg:string)=>msg.length > 1)
    const getFomattedMessage = (msg:string) => {
        if(msg.length > 25) {
            return msg.slice(0,25)+'...'
        }
        return msg;
    }
    const onMouseIn = (e: React.MouseEvent<HTMLElement>) => {
        const { bottom, left, top } = e.currentTarget.getBoundingClientRect();
    
        const tooltipHeight =messages.length * 33 /* Height of your tooltip */;
        const viewportHeight = window.innerHeight;
    
        let tooltipTop = (bottom) + 10;
    
        // Check if tooltip overflows on the bottom side
        if (tooltipTop + tooltipHeight > viewportHeight) {
            tooltipTop = (top) - tooltipHeight;
        }
    
        setErrorCellPosition({
            left: left *currGridZoom * currScreenZoom,
            top: tooltipTop
        });
    
        setIsToolTipOpen(true);
    }


    const onMouseOut = ()=>{
        setIsToolTipOpen(false)
    }

    // return(
    //     <>
    //     {message ? 
    //         <SCContainer>
    //             <img src="/assets/img/VectorFLOW/NMS/error-orange.svg" width={17} height={17} style={{marginRight:'7px',marginLeft:'5px'}}/>
    //             {getFomattedMessage(message)}
    //         </SCContainer>
    //         :
    //         <></>
    //     }
    //     </>
        
    // )
    return (
        <>
            {message &&
            <SCContainer style={{overflow:'visible'}}  themeUi={themeUi} >
                <img src="/assets/img/VectorFLOW/NMS/error-orange.svg" width={17} height={17} style={{marginRight:'7px',marginLeft:'5px'}} onMouseEnter={onMouseIn} onMouseLeave={onMouseOut} data-testid="warningImage"/>
                <p  >{getFomattedMessage(message)}</p>
                {isToolTipOpen && (
                    <Portal wrapperId="error-tooltip">
                        <SCToolTipWrapper themeUi={themeUi} data-testid='tooltip-wrapper' style={{...errorCellPosition}} onMouseEnter={()=>setIsToolTipOpen(true)} onMouseLeave={onMouseOut}>
                            <SCErrorToolTipUl>
                                {(messages && messages.length>0) &&  messages.map((sentence:string,index:number)=>{
                                    return <SCErrorToolTipLi key={index}>{sentence}</SCErrorToolTipLi>
                                })}
                            </SCErrorToolTipUl>
                        </SCToolTipWrapper>
                    </Portal>
                )}
            </SCContainer>
        }
        </>
    )
}

export default WarningCell;