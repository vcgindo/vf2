import styled from "styled-components";
import * as globalStyles from "../../../../../styles/global";

export const Wrapper = styled.div`
  width: 100%;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  // & .ag-header-container {
  //   font-size: 18px;
  // }
  & .ag-header-cell-text {
    text-align: center;
  }
  & > .ag-theme-alpine {
    margin: 20px 0;
    width: 100%;
  }
  & > button {
    width: max-content;
  }
  & > *:not(button, .toolbar-container) {
    transition: flex 0.2s ease-in-out !important;
    flex: 1;
  }
  & .toolbar-container {
    width: 100%;
    margin-bottom: 0;
    margin-top: 20px;
    padding-left: 0;
    margin-left: 0;
  }

  & > div[data-testid="vf_pagination"]{
    flex: unset;
    width:100%;
    margin-top: -20px;
  }
  & .chart-wrapper {
    position: relative;
    width: 100%;
    max-height: 40vh; // or whatever height you want

    > div{
      height: 100% !important;
      & .ag-charts-wrapper{
        max-height: 100% !important;
        .ag-charts-canvas{
          height: 100%;
          >canvas{
            height:100% !important;
          }
        }
      }
    }

    & .chart-scroll{
      height:95% !important;
      width:"100%";
    }
  }
`;

export const Button = styled.button<{ themeUi: string; arrowName: string }>`
  padding: 1rem 2rem;
  line-height: 1;
  border-radius: 10px 10px 0 0;
  font-size: 10px;
  position: relative;
  background: ${(props) =>
    globalStyles.chooseThemeColor[props.themeUi]?.color4};
  color: ${(props) => globalStyles.chooseThemeColor[props.themeUi]?.colorText};
  &:after {
    content: "";
    position: absolute;
    left: 50%;
    top: -3px;
    transform: translate(-50%, -50%);
    border: 2px solid white;
    width: 20px;
    height: 20px;
    background: black;
    font-family: Roboto;
    border-radius: 50%;
    background: url(/assets/img/mto/fullKitAssignment/${(props) =>
    props.arrowName}.svg);
    background-position: center;
    background-repeat: no-repeat;
    background-size: contain;
  }
`;

export const BTRAvailabiltyCellRendererWrapper = styled.div`
    height:100%;
    width:100%;
    display:flex;
    align-items:center;
    justify-content:center;
`

/***Analytical screen css */
export const BPRDailyAnalyticsWrapper = styled.div`
    padding:0px;
    display:flex;
    flex-direction:column;
    align-items:center;
    
`

export const BPRDailyAnalyticsContainer = styled.div`
    display:flex;
    flex-direction:column;
    width:95%;
    background: #383737 0% 0% no-repeat padding-box;
    box-shadow: 0px 6px 12px #00000034;
    padding:4px 8px;
    border-radius:4px;
`

export const BPRDailyAnalyticsHeader = styled.div`
   color:white; 
   margin-bottom:6px;
   //border-bottom:1px white solid;
`

export const BPRDailyAnalyticsTableContainer = styled.div`

`

export const BPRDailyAnalyticsTableHeaderContainer = styled.div`
    display:flex;
    flex-direction:row;
    color:white;
    font-size: 8px;
    width:100%
`

export const BPRDailyAnalyticsTableHeader = styled.div`
    width:100%;
    text-align: center;
    font-size: 10px;
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

export const BPRDailyAnalyticsTableCellHeader = styled.p`
    font-style:normal;
    font-variant:normal;
    font-weight:500;
    font-size:16px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #313131;
`
