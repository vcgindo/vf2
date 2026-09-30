import styled from "styled-components";

import * as globalStyles from '../../../../styles/global'

export const StepperWrapper = styled.div`
    height: 58px;
    width:100%;
    display:flex;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    border: 0.5px solid #00000029;
    border-radius:8px;
`

export const StepWrapper = styled.div`
    display:flex;
    align-items:center;
    width:100%;
`

export const StepSection = styled.div`
    height:100%;
    // width:100%;
   
`


export const StepIconWrapper = styled.div`
    height:100%;
    width:100%;
    display:flex;
    align-items:center;
    margin-left:20px;
    margin-right:5px;
`

export const StepIcon  = styled.img`
    width: 18px;
    height: 18px;
`

export const StepLabel = styled.div<{themeUi:string}>`
    font-family:Roboto;
    font-size:18px;
    font-weight:medium;
    display:flex;
    align-items:center;
    height:100%;
    margin-right:20px;
    color:${(props)=>globalStyles.chooseThemeColor[props.themeUi].color5};
`
export const StepStrokeWrapper = styled.div`
    height:100%;
    width:100%;
    display:flex;
    align-items:center;
`

export const StepStroke = styled.div`
    height:3px;
    width:100%;
    background-color:#00000029;
`