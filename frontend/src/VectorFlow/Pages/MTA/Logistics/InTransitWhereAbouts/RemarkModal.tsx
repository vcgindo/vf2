import { useUserData } from "../../../../../context"
import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard"
import { ButtonWrapper, RemarkDate, RemarkModalContentWrapper, RemarkModalRemarkCelLRenderer, RemarkModalTable, RemarkModalTableCell, RemarkModalTableHeader, RemarkModalTableHeaderContainer, RemarkModalTableRow, RemarkModalTableRowContainer, RemarkText } from "./styles"
import UserIcon from "./UserIcon"
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton"

interface RemarkModalProps{
    isOpen:boolean
    onClose:()=>void
    data:Array<any>
}

const RemarkModal = (props:RemarkModalProps)=>{

    const {
        isOpen,
        onClose,
        data
    } = props

    const {user} = useUserData()
    const theme_ui = user.user.theme_ui

    return(
        <VFModalCard openModal={isOpen} headerIcon="/assets/img/VectorFLOW/BPR/remark.svg" headerText="Remarks" closeIcon="/assets/img/VectorFLOW/NMS/close-white.svg" closeModal={onClose}>
            <RemarkModalContentWrapper>
                <RemarkModalTable className="custom-scrollbar">
                    <RemarkModalTableHeaderContainer>
                        <RemarkModalTableHeader style={{textAlign:'center', paddingRight:'5px'}}>
                            Name
                        </RemarkModalTableHeader>
                        <RemarkModalTableHeader>
                            Remarks
                        </RemarkModalTableHeader>
                        <RemarkModalTableHeader>
                            ETA
                        </RemarkModalTableHeader>
                        <RemarkModalTableHeader>
                            Current Location
                        </RemarkModalTableHeader>
                    </RemarkModalTableHeaderContainer>
                    <RemarkModalTableRowContainer>
                        {(!data || data.length===0)?(
                            <p style={{textAlign:'center',height:200}}>No data to show</p>
                        ):(
                            data.map((d:any,index:number)=>{
                                return(
                                <RemarkModalTableRow key={index} style={{borderTop:index===0?'none':'dashed 1px gray'}}>
                                    <UserIcon data={d.UserName}/>
                                    <RemarkModalTableCell>
                                        <RemarkModalRemarkCelLRenderer>
                                            <RemarkText>
                                               {d.Remarks}
                                            </RemarkText>
                                            <RemarkDate>
                                               {d.RemarksDate}
                                            </RemarkDate>
                                        </RemarkModalRemarkCelLRenderer>
                                    </RemarkModalTableCell>
                                    <RemarkModalTableCell>
                                       {d.ETA}
                                    </RemarkModalTableCell>
                                    <RemarkModalTableCell>
                                       {d.CurrentLocation}
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

export default RemarkModal