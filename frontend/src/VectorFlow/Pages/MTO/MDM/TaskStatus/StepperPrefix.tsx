import { StepperPrefixIcon, StepperPrefixLabel, StepperPrefixSubLabel, StepperPrefixWrapper } from "./styles"


interface StepperPrefixProps{
    label:string
    subLabel:string
}

const StepperPrefix = (props:StepperPrefixProps)=>{
    
    return(
        <StepperPrefixWrapper>
            <StepperPrefixIcon src="/assets/img/VectorFLOW/NMS/task-status-user.svg"/>
            <StepperPrefixLabel>
                {props.label}
            </StepperPrefixLabel>
            <StepperPrefixSubLabel>
                {`(${props.subLabel})`}
            </StepperPrefixSubLabel>
        </StepperPrefixWrapper>
    )
}

export default StepperPrefix