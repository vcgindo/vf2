
import { BPRSubmitRemarkToolTipProps } from "../../../../../VectorFlow/types/BPR"
import Portal from "../../../../../components/VectorFLOW/layouts/Portal"

import * as globalStyles from '../../../../../styles/global'
import {
    BPRRemarksToolTipWrapper, 
    BPRRemarksToolTipContent,
    BPRRemarkToolTipTextArea,
    BPRRemarkToolTipButtonGroup,
    BPRRemarkToolTipButton
} from "./styles"



const BPRSubmiRemarkToolTip = (props:BPRSubmitRemarkToolTipProps)=>{

    const {
        style,
        remark,
        setRemark,
        onClose,
        onSuccess,
        isDate,
        themeUi
    } = props

    const currBgColor = globalStyles.chooseThemeColor[themeUi].color5

    return(
        <Portal wrapperId="tooltip">
            <BPRRemarksToolTipWrapper style={{...style}}>
                <BPRRemarksToolTipContent  className="custom-scrollbar">
                    {isDate?<input style={{width:'147px', marginBottom:'5px'}} type={'date'}  onChange={setRemark} value={remark} autoFocus/>:<BPRRemarkToolTipTextArea placeholder="Type your remark here" onChange={setRemark} value={remark} autoFocus/>}
                    <BPRRemarkToolTipButtonGroup>
                        <BPRRemarkToolTipButton style={{marginRight:10,backgroundColor:currBgColor,color:'white'}} onClick={onSuccess} >
                            Submit
                        </BPRRemarkToolTipButton>
                        <BPRRemarkToolTipButton style={{border:`1px solid ${currBgColor}`}} onClick={onClose} >
                            Cancel
                        </BPRRemarkToolTipButton>
                    </BPRRemarkToolTipButtonGroup>
                </BPRRemarksToolTipContent>
            </BPRRemarksToolTipWrapper>
        </Portal>
    )
}

export default BPRSubmiRemarkToolTip