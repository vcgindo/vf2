

import { BPRRemarkHistoryToolTipProps } from "../../../../../VectorFlow/types/BPR"
import Portal from "../../../../../components/VectorFLOW/layouts/Portal"

import {
    BPRRemarksToolTipWrapper, 
    BPRRemarksToolTipContent,
    BPRRemarksToolTipContentHeaderContainer,
    BPRRemarksToolTipContentHeader,
    BPRRemarksToolTipContentColumnContainer, 
    BPRRemarksToolTipContentColumn, 
    BPRRemarksToolTipContentRowContainer, 
    BPRRemarksToolTipContentRow, 
    BPRRemarksToolTipContentRowCell ,
    BPRRemarksToolTipContentRowNameCellSection,
    BPRRemarksToolTipContentRowDataCellSection,
    BPRRemarkHistoryCloseIcon,
} from "./styles"

const BPRRemarkHistoryToolTip = (props:BPRRemarkHistoryToolTipProps)=>{

    const {
        style,
        remarkHistory,
        onClose
    } = props

    return(
        <Portal wrapperId="tooltip">
             <BPRRemarksToolTipWrapper style={{...style}}>
                <BPRRemarksToolTipContent>
                <BPRRemarksToolTipContentHeaderContainer>
                    < BPRRemarksToolTipContentHeader>
                            Remarks History
                    </BPRRemarksToolTipContentHeader>
                    <BPRRemarkHistoryCloseIcon src="/assets/img/VectorFlow/NMS/close-dark.svg" alt="close-icon" onClick={onClose}/>
                </BPRRemarksToolTipContentHeaderContainer>
                
                <BPRRemarksToolTipContentColumnContainer>
                    <BPRRemarksToolTipContentColumn style={{width:140}}>
                        Date
                    </BPRRemarksToolTipContentColumn>
                    <BPRRemarksToolTipContentColumn style={{width:'100%'}}>
                        Remarks
                    </BPRRemarksToolTipContentColumn>
                </BPRRemarksToolTipContentColumnContainer>
                
                    <BPRRemarksToolTipContentRowContainer  className="custom-scrollbar">
                    {remarkHistory.map((r:any)=>{
                       if(r){
                        return(
                            <BPRRemarksToolTipContentRow>
                                <BPRRemarksToolTipContentRowCell style={{width:130}}>
                                    {r.rd}
                                </BPRRemarksToolTipContentRowCell>
                                <BPRRemarksToolTipContentRowCell >
                                    {(r.un && r.un.length>0) &&(
                                        <BPRRemarksToolTipContentRowNameCellSection>
                                            Name - {r.un}
                                        </BPRRemarksToolTipContentRowNameCellSection>
                                    )}
                                    <BPRRemarksToolTipContentRowDataCellSection style={{fontWeight:500,color:" #464646"}}>
                                        {r.r}
                                    </BPRRemarksToolTipContentRowDataCellSection>
                                </BPRRemarksToolTipContentRowCell>
                            {/* {Object.keys(r).map((key:string)=>{
                                    if(key==="date" ){
                                        return(
                                            <BPRRemarksToolTipContentRowCell style={{width:130}}>
                                                {r[key]}
                                            </BPRRemarksToolTipContentRowCell>
                                        )
                                    }
                                    if(key==='remark'){
                                        return(
                                            <BPRRemarksToolTipContentRowCell >
                                                <BPRRemarksToolTipContentRowNameCellSection>
                                                    Name - {r.author}
                                                </BPRRemarksToolTipContentRowNameCellSection>
                                                <BPRRemarksToolTipContentRowDataCellSection style={{fontWeight:500,color:" #464646"}}>
                                                    {r.remark}
                                                </BPRRemarksToolTipContentRowDataCellSection>
                                            </BPRRemarksToolTipContentRowCell>
                                        )
                                    }
                            })} */}
                            </BPRRemarksToolTipContentRow>
                            )
                       }
                    })}
                </BPRRemarksToolTipContentRowContainer>
                
                </BPRRemarksToolTipContent>
            </BPRRemarksToolTipWrapper>
        </Portal>
    )
}

export default BPRRemarkHistoryToolTip