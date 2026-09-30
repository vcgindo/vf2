import React from "react"
import { DBMSuggestionsReasonsToIdMapper } from "../../../../../helpers/BPRConstants"
import { SuggestionCategoryIcon } from "./styles"
import Tooltip from "../../../../../VectorFlow/Pages/MTO/Common/Tooltip"


const SuggestionCategoryCellRenderer = (params:any)=>{

    const  upwards =["1","2","3","4","6","7","8","9","10"]

    const Comment:any = params.data.Comment

    const CommentId:any = DBMSuggestionsReasonsToIdMapper[Comment]

    return(
        <Tooltip content={<p style={{textAlign:'center', fontSize: '10px', padding: '12px'}}>{Comment}</p>}>
        <React.Fragment>
           {(upwards.includes(CommentId))?<SuggestionCategoryIcon src='/assets/img/VectorFLOW/BPR/analytics-increase.svg' /> :<SuggestionCategoryIcon style={{transform:'rotate(90deg)'}} src='/assets/img/VectorFLOW/BPR/analytics-decrease.svg' />}
        </React.Fragment>
        </Tooltip>
    )
}

// src='/assets/img/VectorFLOW/BPR/analytics-increase.svg'

export  default SuggestionCategoryCellRenderer