import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard"
import { ContactModalContentHeader, ContactModalContentValue, ContactModalContentWrapper } from "./styles"


interface ContactDetailsModalProps{
    isOpen:boolean
    onClose:()=>void
    data:any
}

const ContactDetailsModal =(props:ContactDetailsModalProps)=>{

    const {
        isOpen,
        onClose,data
    } = props

    return(
        <VFModalCard openModal={isOpen} headerIcon="/assets/img/VectorFLOW/BPR/user.svg" headerText="Contact Details" closeIcon="/assets/img/VectorFLOW/NMS/close-dark.svg" closeModal={onClose}>
            <ContactModalContentWrapper>
                <ContactModalContentHeader>
                    Name
                </ContactModalContentHeader>
                <ContactModalContentValue>
                    {data.TransporterName}
                </ContactModalContentValue>
                <ContactModalContentHeader>
                    Phone No
                </ContactModalContentHeader>
                <ContactModalContentValue>
                    {data.TransporterContact}
                </ContactModalContentValue>
                <ContactModalContentHeader>
                    Email ID
                </ContactModalContentHeader>
                <ContactModalContentValue>
                    {data.TransporterEmail}
                </ContactModalContentValue>
            </ContactModalContentWrapper>
        </VFModalCard>
    )
}

export default ContactDetailsModal