
import { CSSProperties,  useRef, useState } from "react"
import Portal from "../../../../../components/VectorFLOW/layouts/Portal"


import {ConflictErrorToolTipSection, ConflictErrorToolTipWrapper,ConflictErrorText, ToolTipTriangle} from './styles' 
import { useUserData } from "../../../../../context"



const ConflictErrorCellRenderer = (params:any)=>{


    const {user} = useUserData()

    const toolTipRef = useRef<HTMLDivElement>(null)

    const themeUi = user.user.theme_ui

    const conflictTextColor = themeUi==="REGALBLAZE"?"rgb(164 104 6)":"rgb(130, 15, 76)"


    const currScreenZoom = 1
    const currGridZoom = 1

    const [isToolTipOpen,setIsToolTipOpen] = useState(false)
    const [tooltipPosition,setToolTipPosition] = useState<CSSProperties>()
    const [isToolTipOverflowing,setIsToolTipOverflowing] = useState<boolean>(false)

    const currColumn = params.colDef?.colId || ''


    const getTextColor = () => {
        let conflictFound = false;
        const currentColId = params.colDef?.colId;
        const currentRow = params.data;
    
        if (!currentRow.users) return 'black';
        currentRow.users.some((user: any) => {
            if (currentColId) {
                if (user.data[currentColId] !== currentRow[currentColId]) {
                    conflictFound = true;
                    return true; 
                }
            }
            return false;
        });
        if (conflictFound) {
            return conflictTextColor;
        }
        return 'black';
    }


    const onMouseIn = (e: any) => {


        setIsToolTipOpen(true)

       setTimeout(()=>{
        if(toolTipRef.current){
        const viewportHeight = window.innerHeight;
        // const viewPortWidth = window.innerWidth

        const {height:toolTipHeight,width:tooltipWidth} = toolTipRef.current.getBoundingClientRect()

        
        const { left, top,height:targetHeight,width:targetWidth} = e.target.getBoundingClientRect();
        
        // const tooltipHeight = params.data.users.length * 40;
        // const viewportHeight = window.innerHeight;
        // const viewPortWidth = window.innerWidth
    
    
        let tooltipTop = (top * currGridZoom * currScreenZoom) +targetHeight;
        // let tooltipLeft = (left *  currGridZoom * currScreenZoom) +((targetWidth/2)*  currGridZoom * currScreenZoom) - (toolTipWidth/2);
        const tooltipLeft = (left *  currGridZoom * currScreenZoom) +((targetWidth/2)*  currGridZoom * currScreenZoom) - (tooltipWidth/2) ;


    
        //check for tooltip's overflow
        if (tooltipTop + toolTipHeight > viewportHeight) {
            //if it overflows render it above the cell
            tooltipTop = top *  currGridZoom * currScreenZoom - toolTipHeight ;
            //if it renders outside the viewport align it to the left
            // if(tooltipTop<10){
            //     tooltipTop=10
            //     if(tooltipLeft + toolTipWidth< viewPortWidth){
            //         tooltipLeft = tooltipLeft  +toolTipWidth
            //     }
            //     else{
            //         tooltipLeft = tooltipLeft  -toolTipWidth
            //     }
            // }
            setIsToolTipOverflowing(true)
        }
        setToolTipPosition({           
            left: tooltipLeft,
            top: tooltipTop
        });
        }
        
       },0)
    }

    

    const onMouseOut = ()=>{
        setIsToolTipOpen(false)
        setToolTipPosition({           
            left: 0,
            top: 0
        });
        setIsToolTipOverflowing(false)
    }


    

    return(
        <div style={{height:'100%',width:'100%',textAlign:'center',padding:'0px 14px'}} onMouseEnter={onMouseIn} onMouseLeave={onMouseOut}>
            <p  style={{color:getTextColor(),zIndex:-10,textOverflow:'ellipsis',display:"block",overflow:"hidden"}}>
                {params.value}           
            </p>
           {params.data.users && isToolTipOpen && (
             <Portal wrapperId="conflict-tooltip">
                <ConflictErrorToolTipWrapper id={'tooltipWrapper'} ref={toolTipRef} style={{...tooltipPosition}} className="custom-scrollbar">
                    {!isToolTipOverflowing && (    
                        <ToolTipTriangle style={{top:-13}}/>
                    )}
                    {params.data.users.map((user:any,index:number)=>{
                        return (
                            <ConflictErrorToolTipSection key={index} style={{borderBottom:index<params.data.users.length-1?'1px solid gray':'unset'}}>
                                <ConflictErrorText><b>User</b> : {user.user}</ConflictErrorText>
                                <ConflictErrorText><b>{params.colDef?.headerName}</b> : {!user.data[currColumn]?"NULL":user.data[currColumn]}</ConflictErrorText>
                            </ConflictErrorToolTipSection>
                        )
                    })}
                    {isToolTipOverflowing && (
                         
                            <ToolTipTriangle style={{top:'unset',bottom:-14,transform:'rotate(180deg)'}}/>
                    )}
                </ConflictErrorToolTipWrapper>
             </Portal>
           )}
        </div>
    )
}

export default ConflictErrorCellRenderer