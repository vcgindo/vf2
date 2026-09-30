import styled from "styled-components";
import * as globalstyles from '../../../../../styles/global'

export const BPRDailyAnalyticsWrapper = styled.div`
    padding:10px;
    display:flex;
    flex-direction:column;
    align-items:center;
    
`

export const BPRDailyAnalyticsContainer = styled.div<{ theme: string }>`
    display:flex;
    flex-direction:column;
    width:90%;
    background: ${(props) => props.theme === 'NOIRFUSION' ? globalstyles.chooseThemeColor[props.theme].color3 : '#383737'} 0% 0% no-repeat padding-box;
    color:${(props) => props.theme === 'PUREELEGANCE' ? 'black' : "white"}; 
    box-shadow: 0px 6px 12px #00000034;
    padding:4px 8px;
    border-radius:4px;
`

export const BPRDailyAnalyticsHeader = styled.div<{ theme: string }>`
   color:inherit; 
   margin-bottom:6px;
   border-bottom:1px ${(props) => props.theme === 'PUREELEGANCE' ? 'black' : "white"} solid;
`

export const BPRDailyAnalyticsTableContainer = styled.div`

`

export const BPRDailyAnalyticsTableHeaderContainer = styled.div`
    display:flex;
    flex-direction:row;
    color:inherit;
`

export const BPRDailyAnalyticsTableHeader = styled.div`
    width:100%;
    text-align: left;
    margin-bottom:5px;
`

export const BPRDailyAnalyticsTableRowContainer = styled.div`
    display:flex;
    flex-direction:column;
    justify-content:center;
`

export const BPRDailyAnalyticsTableRow = styled.div`
    display:flex;
    flex-direction:row;
    width:95%;
    border-radius: 4px ;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: 0px 3px 12px #58585829;
    margin-bottom:5px;
    overflow:hidden;
    zoom:0.7;
`

export const BPRDailyAnalyticsTableCell = styled.div`
    
    text-align:center;
    position:relative;
    width:100%;
    display:flex;
    align-items:center;
    justify-content:center;
    flex-direction:column;
    font-weight:500;
    font-size:11px;
    line-height:21px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #313131;
    &:before{
        content:'';
        position:absolute;
        right:0;
        height:100%;
        width:1px;
    }
`

export const BPRDailyAnalyticsTableNoChangeWrapper = styled.div`
    display:flex;
    flex-direction:column;
`

export const BPRDailyAnalyticsTableChangeIcon = styled.img`
    height:10px;
    width:10px;
`

export const BPRDailyAnalyticStatusBar = styled.div`
    display:flex;
    align-items:center;

`

export const BPRDailyAnalyticStatusBarSection = styled.div`
    width:100%;
    font-family:Roboto;
    font-weight:500;
    font-size:12px;  
    line-height:21px;
    letter-spacing: 0px;
    color: inherit;
    text-align:center;
`

export const BPRDailyAnalyticsTableCellHeader = styled.p`
    font-style:normal;
    font-variant:normal;
    font-weight:500;
    font-size:16px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #313131;
`

export const BPRDailyAnalyticsTableCellText = styled.p`
    font-style:normal;
    font-variant:normal;
    font-weight:400;
    font-size:16px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #313131;
`

export const BPRDailyAnalyticsTableCellIcon = styled.img`
    height:20px;
    width:20px;
`

export const InputCheckBox = styled.input<{ theme: string }>`
    display:inline;
    width: 2em;
    height: 2rem;
    accent-color:${(props) => globalstyles.chooseThemeColor[props.theme].color5};
`