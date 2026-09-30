import { useUserData } from "../../../../../context"
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton"
import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard"
import { ButtonWrapper, RemarkDate, RemarkModalContentWrapper, RemarkModalRemarkCelLRenderer, RemarkModalTable, RemarkModalTableCell, RemarkModalTableHeader, RemarkModalTableHeaderContainer, RemarkModalTableRow, RemarkModalTableRowContainer, RemarkText } from "../../Logistics/InTransitWhereAbouts/styles"
import UserIcon from "../../Logistics/InTransitWhereAbouts/UserIcon"
import { FormatDateFunction } from '../../../../../helpers/utils'

interface RemarkModalProps{
    isOpen:boolean
    onClose:()=>void
    data:Array<any>
}

const BPRRemarkHistoryModal = (props:RemarkModalProps)=>{

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
                        <RemarkModalTableHeader style={{textAlign:'center', paddingRight:'10px'}}>
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
                                    <UserIcon data={d.un}/>
                                    <RemarkModalTableCell style={{ paddingLeft:'5px'}}>
                                        <RemarkModalRemarkCelLRenderer>
                                            <RemarkText>
                                               {d.r}
                                            </RemarkText>
                                            <RemarkDate>
                                               {FormatDateFunction(d.rd)}
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

export default BPRRemarkHistoryModal