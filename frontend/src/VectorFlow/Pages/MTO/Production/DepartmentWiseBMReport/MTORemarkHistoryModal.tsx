import { useUserData } from "../../../../../context"
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton"
import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard"
import { ButtonWrapper, RemarkDate, RemarkModalContentWrapper, RemarkModalRemarkCelLRenderer, RemarkModalTableCell, RemarkModalTableHeader, RemarkText } from "../../../MTA/Logistics/InTransitWhereAbouts/styles"
import { RemarkModalTable, RemarkModalTableRowContainer, RemarkModalTableRow, RemarkModalTableHeaderContainer } from "../DepartmentWiseBMReport/styles"
import UserIcon from "../../../MTA/Logistics/InTransitWhereAbouts/UserIcon";
import { memo } from "react";

interface RemarkModalProps{
    isOpen:boolean
    onClose:()=>void
    data:Array<any>
}

const MTORemarkHistoryModal = (props:RemarkModalProps)=>{

    const {
        isOpen,
        onClose,
        data
    } = props

    const {user} = useUserData()
    const theme_ui = user.user.theme_ui
    
    return(

        <VFModalCard openModal={isOpen} headerIcon="/assets/img/VectorFLOW/BPR/remark.svg" headerText="Remark History" closeIcon="/assets/img/VectorFLOW/NMS/close-white.svg" closeModal={onClose}>
            <RemarkModalContentWrapper>
                <RemarkModalTable className="custom-scrollbar">
                    <RemarkModalTableHeaderContainer>
                        <RemarkModalTableHeader style={{textAlign:'center', paddingLeft:'10px'}}>
                            Name
                        </RemarkModalTableHeader>
                        <RemarkModalTableHeader>
                            Remarks
                        </RemarkModalTableHeader>
                    </RemarkModalTableHeaderContainer>
                    <RemarkModalTableRowContainer>
                        {(!data || data.length===0)?(
                            <p style={{textAlign:'center',height:200}}>No data to show</p>
                        ):(
                            data.map((d:any,index:number)=>{
                                return(
                                <RemarkModalTableRow key={index} style={{borderTop:index===0?'none':'dashed 1px gray'}}>
                                    <UserIcon data={d.added_by}/>
                                    <RemarkModalTableCell>
                                        <RemarkModalRemarkCelLRenderer>
                                            <RemarkText>
                                               {d.remark}
                                            </RemarkText>
                                            <RemarkDate>
                                               {d.added_on}
                                            </RemarkDate>
                                        </RemarkModalRemarkCelLRenderer>
                                    </RemarkModalTableCell>
                                </RemarkModalTableRow>
                                )
                            })
                        )}
                    </RemarkModalTableRowContainer>
                </RemarkModalTable>
                <ButtonWrapper>
                    <VFButton
                        onClick={onClose}
                        themeUi={theme_ui}
                    >
                        Go Back!
                    </VFButton>
                </ButtonWrapper>
            </RemarkModalContentWrapper>
        </VFModalCard>
    )
}

export default memo(MTORemarkHistoryModal)
 