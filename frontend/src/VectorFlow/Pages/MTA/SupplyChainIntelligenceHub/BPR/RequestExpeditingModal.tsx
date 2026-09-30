import {useState} from 'react'
import { useUserData } from "../../../../../context"
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton"
import VFButtonOutline from "../../../../../components/VectorFLOW/commons/VFButtonOutline"
import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard"
import { RequestExpeditingModalContent, RequestExpeditingModalInput,RequestExpeditingModalButtonGroup } from "./styles"

interface RequestExpeditingModalProps{
    isOpen:boolean
    onClose:()=>void
    onSubmit:(params:string)=>void
}

const RequestExpeditingModal = (props:RequestExpeditingModalProps)=>{

    const {
        isOpen,
        onClose,
        onSubmit
    } = props

    const [remark,setRemark] = useState<string>('')

    const {user} = useUserData()
    const themeUi = user.user.theme_ui


    return (
        <VFModalCard openModal={isOpen} closeModal={onClose} headerText='Request Expediting' headerIcon='' closeIcon="/assets/img/VectorFLOW/NMS/close-dark.svg" paddingLeftAndRight={0}>
           <RequestExpeditingModalContent>
                <RequestExpeditingModalInput placeholder="Type your message something like ‘Need stock for SKU no - 879777979789723’" value={remark} onChange={(e)=>setRemark(e.currentTarget.value)}/>
                <RequestExpeditingModalButtonGroup>
                    <VFButtonOutline onClick={onClose} themeUi={themeUi} >
                        Go Back!
                    </VFButtonOutline>
                    <VFButton themeUi={themeUi} onClick={()=>{
                        onSubmit(remark)
                        setRemark('')
                    }}>
                        Submit
                    </VFButton>
                </RequestExpeditingModalButtonGroup>
           </RequestExpeditingModalContent>
        </VFModalCard>)
    }

export default RequestExpeditingModal