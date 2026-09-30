import VFButton from "../../../../../components/VectorFLOW/commons/VFButton"
import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard"
import { RadioContainer, SubmitButtonWrapper, RadioButtonGroup, ButtonSeperator } from "./styles"
import { useUserData } from "../../../../../context";

interface ApproveAllModalProps{
    onSuccess:(status:string)=>void;
    onClose:()=>void;
    setSelectionType:any;
}

const ApproveAllModal=(props:ApproveAllModalProps)=>{

    const {
        onSuccess,
        onClose,
        setSelectionType
    } = props

    const {user} = useUserData()

    const themeUi = user.user.theme_ui

    return(
        <VFModalCard headerText={'Approve All'} closeModal={onClose} openModal={true} headerIcon={"/assets/img/VectorFLOW/NMS/approveall.svg"} closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"}>
            <RadioContainer style={{display:'flex', alignItems:'center',flexDirection: 'row', marginTop:'10px'}}>
                <RadioButtonGroup themeUi={themeUi}> 
                    <input type="radio" value="option1" onChange={()=>setSelectionType('All')} name="Approve" id="ApproveAll"/>
                    <label htmlFor="ApproveAll" style={{fontSize:'15px', fontWeight:'300px'}}>Approve across all the pages</label>
                </RadioButtonGroup>  
                <ButtonSeperator/>
                <RadioButtonGroup themeUi={themeUi}> 
                    <input type="radio" value="option2" onChange={()=>setSelectionType('Current')} name="Approve" id="ApproveCurrent"/>
                    <label htmlFor="ApproveCurrent" style={{fontSize:'15px', fontWeight:'300px'}}>Approve only the current page</label>
                </RadioButtonGroup> 
            </RadioContainer>
            <SubmitButtonWrapper>
                <VFButton themeUi={user.user.theme_ui} onClick={() => onSuccess('Approved')}>Ok</VFButton>
            </SubmitButtonWrapper>
        </VFModalCard>
    )
}

export default ApproveAllModal
