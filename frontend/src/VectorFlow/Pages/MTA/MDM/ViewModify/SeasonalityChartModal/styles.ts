import styled from "styled-components";

import * as globalStyles from '../../../../../../styles/global'

export const SCSeasonalityContainer = styled.div`
    padding-top:20px;
    padding-bottom:20px;
    display:flex;
    width:1810px;
    height:850px;

    @media (min-width:1024px) and (max-width:1688px){
        width:1100px;
        height:520px;
    } 
    
`

export const SCChartContainer = styled.div`
    margin-right:33px;
    width:71%;
`

export const SCSeasonalityStatusDetails = styled.div`
    width:20%;
    height:100%;
    box-shadow: -6px 6px 16px #0000000F;
    @media (min-width:1024px) and (max-width:1688px){
        zoom:0.8;
    }
    
`
export const SCSeasonalityDetailsTitle = styled.div<{themeUi:string}>`
    background-color:${(props)=>props.themeUi==="PUREELEGANCE"?'black':globalStyles.chooseThemeColor[props.themeUi].color1};
    color:white;
    font-family:'Roboto';
    font-size:18px;
    letter-spacing:0px;
    font-weight:500;
    letter-spacing: 0px;
    height:53px;
    border-radius: 4px 4px 0px 0px;
    display:flex;
    justify-content:center;
    align-items:center;
`

export const SCText = styled.p<{fontWeight:number,fontSize:number}>`
    font-family:'Roboto';
    letter-spacing: 0px;
    font-weight:${props => props.fontWeight};
    font-size:${props => props.fontSize}px;
    margin:12px 0px;
`

export const SCSeasonalityDetailsBody = styled.div`
    display:flex;
    flex-direction:column;
    // height:77%;
    padding:8px;
    @media (min-width:1024px) and (max-width:1688px){
        zoom:0.8;
    } 
`

export const SCCheckBoxRow = styled.div`
    display:flex;
`

export const SCCheckBoxContainer = styled.div`
    display:inherit;
    align-items:center;
    margin-right:20px;
    
`

export const SCHorizontalDivider = styled.hr`
    width:100%;
    border: none;
    border-top:1px dashed #B2B2B2;
`

export const SCDataRow = styled.div`
    display:flex;
    justify-content:space-evenly;
    align-items:center;
    
`

export const SCDataNode = styled.div`
    width:151px;

`
export const SCVerticalDivider = styled.div`
    width:0.5px;
    background-color:#707070;
    height:45px;
    margin-right:16px;
    margin-left:16px;


`

