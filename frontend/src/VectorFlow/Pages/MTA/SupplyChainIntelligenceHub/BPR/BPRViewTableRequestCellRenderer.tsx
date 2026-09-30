import { useUserData } from "../../../../../context"
import { BPRViewTableRequestCellRendererImg, BPRViewTableRequestCellRendererText, BPRViewTableRequestCellRendererWrapper } from "./styles"

interface BPRViewTableRequestCellRendererProps{
    onClick:()=>void
}

const BPRViewTableRequestCellRenderer = (props:BPRViewTableRequestCellRendererProps)=>{

    const {
        onClick
    } = props

    const {user} = useUserData()

    const themeUi = user.user.theme_ui

    return (
        <BPRViewTableRequestCellRendererWrapper onClick={onClick}>
            <BPRViewTableRequestCellRendererImg src={themeUi==="REGALBLAZE"?"/assets/img/VectorFlow/BPR/add-circle-regal.svg":"/assets/img/VectorFlow/BPR/add-circle.svg"}/>
            <BPRViewTableRequestCellRendererText style={{color:themeUi==="REGALBLAZE"?"#FCA311":"rgb(188, 61, 129)"}}>Request</BPRViewTableRequestCellRendererText>
        </BPRViewTableRequestCellRendererWrapper>
    )

}

export default BPRViewTableRequestCellRenderer