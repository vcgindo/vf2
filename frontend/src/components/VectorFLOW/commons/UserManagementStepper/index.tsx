import { StepIcon, StepIconWrapper, StepLabel, StepperWrapper, StepSection,StepStroke,StepStrokeWrapper,StepWrapper } from "./styles"

type StepState = "completed" |  "active" | "pending"

interface UserManagementStepperProps{
    list:Array<UserManagementStepperListProps>
    themeUi:string
}

interface UserManagementStepperListProps{
    label:string,
    currentState:StepState
}

interface StepComponentProps {
    label:string
    currentState:StepState
    isLast:boolean
    themeUi:string
}

const UserManagementStepper = (props:UserManagementStepperProps)=>{

    const {
        list,
        themeUi
    } = props

    return(
        <StepperWrapper>
            {list.map((s,index)=>{
                return(
                    <UserManagementStepperItem
                        label={s.label}
                        currentState={s.currentState}
                        isLast={index===list.length-1}
                        themeUi={themeUi}
                        key={index}
                    />
                )
            })}
        </StepperWrapper>
    )
}


const UserManagementStepperItem = (step:StepComponentProps)=>{

    const {
        currentState,
        label,
        isLast,
        themeUi
    } = step

    const getImgSrc = (state:StepState):string=>{
        console.log(state)
        if(state==='completed') return "/assets/img/step-completed.svg"
        if(state==='active')return themeUi==="REGALBLAZE"?"/assets/img/step-active-regal.svg":"/assets/img/step-active.svg"
        return "/assets/img/step-pending.svg"
    }

    return(
        <StepWrapper style={{width:isLast?"auto":"100%"}}>
            <StepSection>
                <StepIconWrapper>
                    <StepIcon src={getImgSrc(currentState)}/>
                </StepIconWrapper>
            </StepSection>
            <StepSection >
                <StepLabel themeUi={themeUi}>
                    {label}
                </StepLabel>
            </StepSection>
            {!isLast && (
                <StepSection style={{width:'100%'}}>
                   <StepStrokeWrapper>
                        <StepStroke/>
                   </StepStrokeWrapper>
                </StepSection>
            )}
        </StepWrapper>
    )
}

export default UserManagementStepper