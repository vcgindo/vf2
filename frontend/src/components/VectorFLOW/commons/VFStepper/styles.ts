import styled from "styled-components";

const getProgressColor = (status:string)=>{
    if(status=='completed'){
        return '#5D804E'
    }
    return '#9A9A9A'
}



export const VFStepperWrapper = styled.div`
    display:flex;
    flex-direction:row;
    width:100%;
`

export const VFStepWrapper = styled.div<{isLast:boolean}>`
    display:flex;
    flex-direction:row;
    
`

export const VFStepLabelWrapper = styled.div`
    position:relative;
    display:flex;
    flex-direction:column;
    align-items:center;
    width:60px;
`


export const VFStepLabel = styled.div`
    text-align:center;
    margin-top:6px;
    font-size:16px:
    font-style:normal;
    font-variant:normal;
    font-weight:400;
    // width:100px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #313131;
    white-space:nowrap;
`
export const VFStepDescription = styled.div`

    font-size:12px:
    font-style:normal;
    font-variant:normal;
    font-weight:300;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #1C1E2B;
`

export const VFStepProgress = styled.div<{status:string}>`
    margin-top:12px;
    margin-left:10px;
    margin-right:10px;
    height: 0px;
    outline: 2px ${(props)=>props.status=='async'?'dashed':'solid'} ${(props)=>getProgressColor(props.status)};
`

export const VFStepPrefixWrapper = styled.div`
    margin-bottom:10px;
`

export const VFStepperContentWrapper = styled.div`
    display:flex;
    flex-direction:column;
    align-items:center;
`