import styled from "styled-components"
import { BPRViewTableToolTip } from "../../SupplyChainIntelligenceHub/BPR/styles"

import * as globalStyles from '../../../../../styles/global'

export const CurrentLocationCellRendererWrapper = styled.div`
    border: 0.5px solid #C6C6C6;
    border-radius: 2px;
    height:90%;
    margin-top:2px;
    width:90%;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
`

export const ColorGroupCellRendererWrapper = styled.div`
    display:flex;
    flex-direction:row;
    align-items:center;
    height:100%;
`
export const ColorGroupColorCell = styled.div`
    position:relative;
    height: 31px;
`

export const ColorGroupColorCellToolTip = styled.div<{triangleColor:string}>`
    font-weight:500;
    display:flex;
    justify-content:center;
    align-items:center;
    height: 60px;
    width:150px;
    position:fixed;
    z-index:2000;
    border-radius:8px;
    box-shadow: rgba(60, 64, 67, 0.3) 0px 1px 2px 0px, rgba(60, 64, 67, 0.15) 0px 1px 3px 1px;
    &::after {
        content: '';
        position: absolute;
        top: 100%; /* Position it below the tooltip */
        left: 50%;
        margin-left: -5px; /* Adjust to center the triangle */
        border-width: 5px;
        border-style: solid;
        border-color: transparent transparent ${(props)=>props.triangleColor} transparent; /* Triangle color */
        transform:rotate(180deg);
    }
`

export const MasterDetailWrapper = styled.div`
    display:flex;
    height:100%;
    flex-direction:column;
    padding:10px 0px;
    padding-bottom:40px;
`

export const MasterDetailHeaderWrapper = styled.div`
    width:100%;
    display:flex;
    align-items:center;
    justify-content:space-between;
    padding:0px 20px;
`

export const  MasterDetailHeader = styled.p`
    font-size:20px;
    line-height:21px;
    font-weight:500;
`

export const ContactModalContentWrapper = styled.div`
    display:flex;
    flex-direction:column;
`

export const ContactModalContentHeader = styled.p`
    font-family:Roboto;
    font-size:16px;
    font-weight:300;
    opacity:0.7;
    margin-bottom:3px;
`

export const ContactModalContentValue = styled.p`
    font-family:Roboto;
    font-size:20px;
    font-weight:500;
    margin-bottom:10px;

`

export const RemarkModalContentWrapper = styled.div`
    display:flex;
    flex-direction:column;
    margin:0 -74px;
`

export const RemarkModalTable = styled.div`
    display:flex;
    flex-direction:column;
    // padding:0px 10px;
    padding-left:5px;
    margin-bottom:10px;

`

export const RemarkModalTableHeaderContainer = styled.div`
    display:grid;
    grid-template-columns:60px 300px 90px 90px;
    border-bottom:solid 1px #707070;
    padding:0 14px;
`

export const RemarkModalTableHeader = styled.p`
    font-family:Roboto;
    font-size:12px;
    font-weight:500;
    height:40px;
    display:flex;
    align-items:center;
    // padding:0px 5px;
    white-space: nowrap;
`

export const RemarkModalTableRowContainer = styled.div`
    display:flex;
    flex-direction:column;
    margin-top:10px;
    padding:0 10px;
    max-height:300px;
    // overflow-y:auto;
`
export const RemarkModalTableRow = styled.div`
    display:grid;
    grid-template-columns:60px 300px 90px 90px;
    width:100%;
    margin-bottom:10px;
    padding-top:5px;
`

export const RemarkModalTableCell = styled.div`
    font-family:Roboto;
    font-size:10px;
    font-weight:500;
    position:relative;
`

export const RemarkModalUserIcon = styled.div`
    width:42px;
    height:42px;
    background: #CCCCCC 0% 0% no-repeat padding-box;
    border-radius:50%;
    font-family:Roboto;
    font-size:16px;
    font-weight:500;
    display:flex;
    align-items:center;
    justify-content:center;
    cursor:default;
`

export const RemarkModalRemarkCelLRenderer = styled.div`
    display:flex;
    flex-direction:column;
`

export const RemarkText = styled.p`
    font-family:Roboto;
    font-size:10px;
    font-weight:500;
`

export const RemarkDate = styled.p`
    font-family:Roboto;
    font-size:10px;
    font-weight:500;
    opacity:0.7;
`

export const ButtonWrapper = styled.div`
    width:100%;
    display:flex;
    justify-content:flex-end;
    padding:20px 20px 20px 0px;
    border-top:solid 1px #707070;
    zoom:0.8;
`

export const ETACellRendererCellValue = styled.div`
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: 0px 6px 12px #77777729;
    border: 0.4000000059604645px solid #707070;
    border-radius: 2px;
    height:40px;
    width:100%;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    // padding:4px;
    `

export const UserToolTip = styled(BPRViewTableToolTip)`
    position:absolute;
    max-width:none;
    left:60px;
    top:7px;
    padding-left:10px;
    padding-right:10px;
    border-radius:6px;
    &::after {
        content: '';
        position: absolute;
        left: -6.5px;
        transform: translate(-50%, -50%);
        border-width: 6px;
        border-style: solid;
        border-color: transparent #4E4E4E transparent transparent; /* Updated to black */
    }
`

export const UserToolTipContent = styled.p`
    font-family:Roboto;
    font-size:13px;
    line-height:20px;
`

export const BPRParticularAnalyticsWrapper = styled.div`
    width:100%;
    display:flex;
    flex-direction:column;
    padding:10px 10px;
`

export const BPRParticularAnalyticsTableWrapper = styled.div<{themeUi:string}>`
    background: ${(props)=>props.themeUi==='NOIRFUSION'?globalStyles.chooseThemeColor[props.themeUi].color3:globalStyles.chooseThemeColor[props.themeUi].color1} 0% 0% no-repeat padding-box;
    color:${(props)=>props.themeUi==='PUREELEGANCE'?'black':"white"}; 
    width:100%;
    display:flex;
    flex-direction:column;
    border-radius:4px;
`

export const BPRParticularAnalyticsTableHeaderWrapper = styled.div`
    display:flex;
    margin:7px 10px;
    border-bottom:1.5px dashed white;
`
export const BPRParticularAnalyticsTableHeader = styled.span`
    width:100%;
    font-family:Roboto;
    font-weight:500;
    
    text-align:center;
    padding-bottom:5px;
`

export const BPRParticularAnalyticsTableRowWrapper = styled.div`
    display:flex;
    flex-direction:column;
    padding:5px 10px;
`

export const BPRParticularAnalyticsTableRow = styled.div`
    width:100%;
    display:flex;
`

export const BPRParticularAnalyticsTableCell = styled.span`
    width:100%;
    font-family:Roboto;
    font-weight:500;
    text-align:center;
    padding-bottom:5px;
`