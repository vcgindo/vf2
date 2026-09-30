import { AgeingCellRendererWrapper } from "./styles"
import React, {useState,CSSProperties} from 'react';
import Portal from "../../layouts/Portal";

import {  BPRViewTableToolTip } from "../../../../VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/BPR/styles"


export const AgeingCellRenderer = (params:any)=>{
    
    const [warningIcon,setWarningIcon] = useState('/assets/img/VectorFLOW/BPR/ageing-warning.svg');

    const [isOpen,setIsOpen] = useState(false)

    const [toolTipPosition,setoolTipPosition] = useState<CSSProperties>({
       
    })

    const onMouseIn = (e:React.MouseEvent<HTMLElement>)=>{
        setWarningIcon('/assets/img/VectorFLOW/BPR/ageing-warning-hover.svg')
        const {top,left} = e.currentTarget.getBoundingClientRect()
        setoolTipPosition({
            top:(top * 0.75 * 0.75) -35,
            left:(left* 0.75* 0.75 ) -27
        })
        setIsOpen(true)
    }

    const onMouseOut = ()=>{
        setWarningIcon('/assets/img/VectorFLOW/BPR/ageing-warning.svg')
        setIsOpen(false)
    }



    if(parseInt(params.data['AgeingOrder'],10) > 0){
        return(
            <React.Fragment>
                <AgeingCellRendererWrapper >
                <img src={warningIcon} onMouseEnter={onMouseIn} onMouseLeave={onMouseOut} height={28} width={28} data-testid="ageing-warning-icon" />
                </AgeingCellRendererWrapper>
                {isOpen && (
                    <Portal wrapperId="viewtable">
                        <BPRViewTableToolTip  style={{top:toolTipPosition.top,left:toolTipPosition.left,width:70}}>
                            <p style={{textAlign:'center'}}>High Ageing</p>
                        </BPRViewTableToolTip>
                    </Portal>
                )}
            </React.Fragment>
        )
    }
    return <></>
    
}