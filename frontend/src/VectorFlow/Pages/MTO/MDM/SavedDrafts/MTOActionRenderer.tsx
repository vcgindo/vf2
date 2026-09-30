import { ICellRendererParams } from "ag-grid-enterprise"
import React from "react"
import { useUserData } from "../../../../../context"
import { ActionButtonWrapper, ActionContainer } from "./styles"


interface ActionRendererProps extends ICellRendererParams{
    onEdit:(id:string)=>void
    onDelete:(id:string)=>void
}

const MTOActionRenderer = (props:ActionRendererProps)=>{

    const {
        data,
        onDelete,
        onEdit
    } = props

    const {user} = useUserData()

    const themeUi = user.user.theme_ui

    return(
        <ActionContainer>
            <ActionButtonWrapper src={themeUi==="REGALBLAZE"?"/assets/img/VectorFLOW/NMS/edit-draft-regal.svg":"/assets/img/VectorFLOW/NMS/edit-draft.svg"} height={16} width={16} onClick={()=>onEdit(data)} data-testid="edit-draft"/>
            <ActionButtonWrapper src={themeUi==="REGALBLAZE"?"/assets/img/VectorFLOW/NMS/delete-draft-regal.svg":"/assets/img/VectorFLOW/NMS/delete-draft.svg"} height={16} width={16} style={{marginLeft:"30px"}} onClick={()=>onDelete(data.DraftId)} data-testid="delete-draft"/>
        </ActionContainer>
    )
}

export default MTOActionRenderer