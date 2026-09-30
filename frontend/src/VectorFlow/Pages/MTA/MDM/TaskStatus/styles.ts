import styled from "styled-components";

export const VFTaskStatusWrapper = styled.div`
    display:flex;
    flex-direction:column;
    background-color:white;
    padding-bottom:30px;
    zoom:var(--default-zoom);
`
export const VFTaskStatusContentWrapper = styled.div`
    display:flex;
    flex-direction:column;
    padding:8px;
    padding-left:20px;
`

export const VFTaskStatusStepperWrapper = styled.div<{gridFraction:string}>`
    margin-top:20px;
    padding-left:120px;
    height:150px;
    width:100%;
    display:grid;
    grid-template-columns:${(props)=>props.gridFraction};
    place-items:center;
    grid-gap:60px;
    background-color:#F0F0F0;
    border-radius:8px;
`

export const VFTastStatusDownloadWrapper = styled.div`
    width:100%;
    height:100%;
    display:flex;
    justify-content:center;
    align-items:center;
`

export const VFTaskStatusStepperLabel = styled.p`
    font-size:18px;
    text-align:center;
    width:100px;
    height:40px;
    display:flex;
    justify-content:center;
    align-items: center;
    text-overflow:ellipsis;
`


export const VFTaskStatusNoData = styled.div`
    width:100%;
    height:90px;
    padding:10px;
    padding-left:60px;
    display:flex;
    align-items:center;
`

export const StepperPrefixWrapper = styled.div`
    display:flex;
    margin-left:-30px;
`

export const StepperPrefixIcon = styled.img`
    height:20px;
    width:20px;
`

export const StepperPrefixLabel = styled.p`
    font-family:Roboto;
    font-weight:500;
    font-size:18px;
    letter-spacing: 0px;
    color: #1C1A1A;
    margin-left:10px;
`

export const StepperPrefixSubLabel = styled.p`
    font-family:Roboto;
    font-weight:400;
    font-size:18px;
    letter-spacing: 0px;
    color: #897E7E;
    margin-left:10px;
`

