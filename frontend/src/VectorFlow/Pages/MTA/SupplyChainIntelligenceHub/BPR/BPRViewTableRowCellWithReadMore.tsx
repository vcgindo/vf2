import { BPRViewTableRowCell,BPRViewTableToolTip } from "./styles"

import Portal from '../../../../../components/VectorFLOW/layouts/Portal'

import 'react-tooltip/dist/react-tooltip.css'
import React, { CSSProperties, useState } from "react"
import useViewPort from "../../../../../hooks/useViewPort"


interface BPRViewTableRowCellWithReadMore{
    value:string
}


const BPRViewTableRowCellWithReadMore = (props:BPRViewTableRowCellWithReadMore)=>{

    const {
        value
    } = props

    

    const {getScreenZoomValue} = useViewPort()

    const screenSize = getScreenZoomValue()

    const [isOpen,setIsOpen] = useState(false)

    const [toolTipPosition,setoolTipPosition] = useState<CSSProperties>({
       
    })

    const onMouseIn = (e:React.MouseEvent<HTMLElement>)=>{
        const {top,left} = e.currentTarget.getBoundingClientRect()
        setoolTipPosition({
            top:top * screenSize -40,
            left:left* screenSize -40
        })
        setIsOpen(true)
    }

    const onMouseOut = ()=>setIsOpen(false)

    return(
        <BPRViewTableRowCell style={{display:'flex',flexDirection:"row",position:'relative',justifyContent:'center'}}>
            <p >{value.slice(0,15)}...</p>
            <p style={{color:'#BC3D81',cursor:'default'}} onMouseEnter={onMouseIn} onMouseLeave={onMouseOut}>Read full </p>
            {isOpen && (
                <Portal wrapperId="viewtable">
                    <BPRViewTableToolTip onMouseEnter={()=>setIsOpen(true)} onMouseLeave={()=>setIsOpen(false)} style={{top:toolTipPosition.top,left:toolTipPosition.left}}>
                        {value}
                    </BPRViewTableToolTip>
                </Portal>
            )}
        </BPRViewTableRowCell>
    )
}

export default BPRViewTableRowCellWithReadMore