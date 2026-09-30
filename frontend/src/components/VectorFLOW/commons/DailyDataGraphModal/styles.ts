import styled from "styled-components";

import * as globalStyles from '../../../../styles/global'

export const SCSeasonalityContainer = styled.div`
    padding-top:20px;
    padding-bottom:20px;
    display:flex;
    width:100%;
    height:100%;

    @media (min-width:1024px) and (max-width:1688px){
        width:1000px;
        height:100%;
    } 
    
`

export const SCChartContainer = styled.div`
    margin-right:33px;
    //width:81%;
    width:90%;
    height:90%;
`

export const SCSeasonalityStatusDetails = styled.div`
    width:20%;
    height:100%;
    box-shadow: -6px 6px 16px #0000000F;
    @media (min-width:1024px) and (max-width:1688px){
        zoom:0.7;
    }
    
`
export const SCSeasonalityDetailsTitle = styled.div<{themeUi:string}>`
    background-color:${(props)=>props.themeUi==="PUREELEGANCE"?'black':globalStyles.chooseThemeColor[props.themeUi].color1};
    // background-color:#292C2E;
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

export const SCText = styled.p<{fontWeight:number,fontSize:number,hideDefaultMargin?:boolean}>`
    font-family:'Roboto';
    letter-spacing: 0px;
    font-weight:${props => props.fontWeight};
    font-size:${props => props.fontSize}px;
    margin:${props => props.hideDefaultMargin ? 0 : 12}px 0px;
    white-space: nowrap;
    overflow:hidden;
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