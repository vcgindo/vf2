import styled from "styled-components";

import * as globalStyles from '../../../../../styles/global'

export const SCChartContainer = styled.div<{height?:string}>`
    padding:5px;
    border-radius:12px;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    // box-shadow: -5px 5px 25px #86868633;
    box-shadow: rgba(0, 0, 0, 0.1) 0px 4px 12px;
    margin-right:5px;
    // margin-top:60px;
    margin-bottom:10px;
    margin-left:20px;
    // height:547px;
    height:${props => props.height ? props.height : 'auto'}
`
export const SCChartLayout = styled.div`
    overflow-y:scroll;
    display:flex;
    height:100%;
    flex-direction:column;
    // margin-top:30px;
`;

export const SCChartHeaderContainer = styled.div`
    background-color:white;
    display:flex;
    justify-content:center;
    align-items:center;
    height: 54px;
   
`

export const SCChartSliderContainer = styled.div`
    display: flex;
    justify-content:space-between;
    justify-content:center;
    gap:13px;
    align-items:center;
    height:55px


`

export const SCChartMainContainer =styled.div`
    display: flex;
    justify-content:space-between;
    
`
export const HorizonHeader = styled.p`
    text-align:center;
    font-weight:500;
    font-size:10px;
`

export const SCChartHeader = styled.p`
    font-weight:500;
    font-size:16px;
    line-height:21px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #000000;
`

export const SCHorizontalDivider = styled.hr`
    width:100%;
    border: none;
    border-top:1px solid #B2B2B2;
`

export const SummaryTableColumn = styled.p<{color:string}>`
    color:${(props)=>props.color};
    font-weight:600;
`

export const AvailabilityContainer = styled.div`
    display:flex;
    flex-direction:column;
    margin-top:58px;
    margin-left:-10px;
    box-shadow: rgb(155 155 155 / 16%) 6px 6px 12px;
    z-index:100;
    border-radius:0px 8px 8px 0px;
`

export const AvailabilityHeader = styled.div`
    position:relative;
    width:250px;
   overflow:hidden;
    min-width:120px;
    height:53px;
    padding:10px;
    padding-top:15px;
    font-style:normal;
    font-variant:normal;
    font-weight:600;
    font-size:13px;
    line-height:13px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #000000;
    // border-bottom: 1px solid #919191B3;
    box-shadow: 0px 6px 12px #9B9B9B29;
    text-align:center;
    &::after{
        content:'';
        position:absolute;
        left:1px;
        top:4px;
        bottom:4px;
        background-color:#898585;
        width:0.5px;
    }
    &:last-child::after {
        display: none;
    }
    white-space:nowrap;
    text-overflow:ellipsis;
    background-color:white;
    border-radius:0px 8px 0px 0px ;
`

export const AvailabilityContent = styled.div<{themeUI:string}>`
    display:grid;
    place-items:center;
    background-color:white;
    height:100%;
    font-size:24px;
    font-weight:500;
    color:${(props)=>globalStyles.chooseThemeColor[props.themeUI].color5};
    border-radius:inherit;
`