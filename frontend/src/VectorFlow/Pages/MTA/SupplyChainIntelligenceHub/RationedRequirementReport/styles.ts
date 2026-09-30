import styled from "styled-components";

import * as globalStyles from  '../../../../../styles/global'

export const RRRLayout = styled.div`
    margin-top:10px;
    margin-left:20px;
// margin-bottom:40px;
`

export const RRRTaskBar  = styled.div`
    position:fixed;
    width:97%;
    right:0;
    top:13vh;
    height:70px;
    background-color:white;
    display:flex;
    flex-direction:row;
    justify-content:flex-end;
    align-items:center;
    gap:20px;
    padding:16px;
    z-index:2;
    transition:0.3s ease 0s;
`


export const RRRColorCellRendererWrapper = styled.div`
    display:flex;
    justify-content:center;
    align-items:center;
    width: 97px;
    height: 34px;
    box-shadow: 0px 6px 12px #8D8D8D29;
    border-radius: 4px;
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
`

export const RRRTagsCellRendererWrapper = styled.div`
    display:flex;
    justify-content:center;
    align-items:center;
    width: 55px;
    height: 25px;
    background: #8E8E8E 0% 0% no-repeat padding-box;
    color: #FFFFFF;
    box-shadow: 0px 6px 12px #8D8D8D29;
    border-radius: 2px;
    font-style:normal;
    font-variant:normal;
    font-weight:medium;
    font-size:14px;
    line-height:19px;
    font-family:Roboto;
    letter-spacing: 0px;
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
`


export const RRRAnalyticsWrapper = styled.div`
    width:100%;
    color:white;
    padding:10px;
    font-family:Roboto;
`
export const RRRAnalyticsContainer = styled.div<{themeUi:string}>`
    display:flex;
    flex-direction:column;
    width:100%;
    background: ${(props)=>props.themeUi==='NOIRFUSION'?globalStyles.chooseThemeColor[props.themeUi].color3:globalStyles.chooseThemeColor[props.themeUi].color1} 0% 0% no-repeat padding-box;
    color:${(props)=>props.themeUi==='PUREELEGANCE'?'black':"white"}; 
    box-shadow: 0px 6px 12px #00000034;
    padding:4px 8px;
    border-radius:4px;
`

export const RRRAnalyticsHeader = styled.div`
    width:100%;
    padding:6px 0px;
    font-size:12px;
`

export const RRRAnalyticsTableContainer = styled.div`
    display:flex;
    flex-direction:column;
`
export const RRRAnalyticsTableHeaderWrapper = styled.div`
    width:100%;
    border-top:dotted 2px gray;
    border-bottom:dotted 2px gray;
    display:flex;

`
export const RRRAnalyticsTableHeader = styled.div`
    width:100%;
    height:40px;
    display:flex;
    font-size: 8px;
    flex-direction:column;
    justify-content:center;
    overflow:hidden;
    text-align:center;
`

export const RRRAnalyticsTableSubHeader = styled.div`
    width:100%;
    height:20px;
    display:flex;
    font-size:8px;
    justify-content:center;
    align-items:center;
`
export const RRRAnalyticsTableSubHeaderSection = styled.div`
    width:100%;
    height:100%;
    font-size:7px;
    display:flex;
    justify-content:center;
    align-items:center;
`

export const RRRAnalyticsSeperator = styled.div<{themeUi:string}>`
    height:10px;
    width:2px;
    background-color:${(props)=>props.themeUi==="PUREELEGANCE"?"black":"white"};
`

export const RRRAnalyticsTableRowContainer = styled.div`
    width:100%;
    display:flex;
    flex-direction:column;
`
export const RRRAnalyticsTableRow = styled.div`
    width:100%;
    display:flex;
    border-bottom:solid 1px white;
    &:last-child {
        border-bottom:none;
    }
`

export const RRRAnalyticsTableCell = styled.div`
    width:100%;
    display:flex;
    align-items:center;
    justify-content:center;
    height:30px;
`

export const RRRAnalyticsTableColorCell = styled.div`
    display:flex;
    width: 15px;
    height: 15px;
    align-items:center;
    border-radius: 2px;
`

export const RRRAnalyticsTableCustomCell = styled.div`
    display:flex;
    width:100%;
    align-items:center;
    justify-content:center;
    overflow:hidden;
`

export const RRRAnalyticsTableColorCellLabel = styled.p`
    margin-left:5px;
`