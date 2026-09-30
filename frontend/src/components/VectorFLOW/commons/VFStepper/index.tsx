import { VFStepperWrapper, VFStepWrapper,VFStepLabel,VFStepProgress, VFStepLabelWrapper, VFStepDescription, VFStepPrefixWrapper, VFStepperContentWrapper } from "./styles"


interface VFStepperProps{
    items:StepItem[]
    width?:string
    zoom?:number
    dashWidth?:string
}

export interface StepItem{
    label:string,
    status:'completed' | 'pending' | 'rejected' 
    description:string
    prefix?:any

}

interface VFStepProps{
    label:string
    status:'completed' | 'pending' | 'rejected'
    index:number
    isLast:boolean
    description:string
    dashWidth?:string
    prefix?:any
}

interface VFStepIconProps{
    status:string
}

const VFStepper =  (props:VFStepperProps)=>{

    const {
        items,
        width,
        zoom=1,
        dashWidth="100px"
    }= props

    return (
        <VFStepperWrapper style={{width:width,zoom:zoom}} data-testid='stepper'>
            {items.map((i,index)=>{
                return <Step dashWidth={dashWidth} label={i.label} status={i.status} key={index} index={index} isLast={index==items.length-1} description={i.description} prefix={i.prefix}/>
            })}
        </VFStepperWrapper>
    )
}

const Step = (props:VFStepProps)=>{

    const {
        label,
        status,
        isLast,
        description,
        dashWidth,
        prefix
    } = props

    return(
        <VFStepWrapper isLast={isLast}>        
            <VFStepLabelWrapper>        
                  {prefix && (
                    <VFStepPrefixWrapper>
                        {prefix}
                    </VFStepPrefixWrapper>
                  )}
                <VFStepIcon status={status}/>
                <VFStepperContentWrapper>
                    <VFStepLabel>{label}</VFStepLabel>
                    <VFStepDescription>{description}</VFStepDescription>
                </VFStepperContentWrapper>
            </VFStepLabelWrapper>
            {!isLast && <VFStepProgress status={status} style={{width:dashWidth,marginTop:prefix?"40px":"12px"}}/>}
        </VFStepWrapper>
    )
}   


const VFStepIcon = (props:VFStepIconProps)=>{
    const {
        status
    } = props

    const getImgSrc = ()=>{
        switch(status){
            case 'completed':
                return '/assets/img/VectorFLOW/NMS/successful.svg'
            case 'rejected':
                return '/assets/img/VectorFLOW/NMS/rejected.svg'
            default:
                return '/assets/img/VectorFLOW/NMS/pending.svg'
        }
    }

    return(
        <img src={getImgSrc()} height={28} width={28} alt={status}/>
    )
}

export default VFStepper