import styled from "styled-components";
import * as globalStyles from "../../../../../styles/global";

export const BPRViewTableHeaderTab = styled.div<{
  status: boolean
  zIndex: number
  marLeft: true | false
  themeUi: string
  bgColor?: string
}>`
  color: ${(props) => (props.status ? '#FFFFFF' : '')};
  opacity: 1;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
  position: relative;
  z-index: ${(props) => props.zIndex};
  margin-left: ${(props) => (props.marLeft ? '-1.5em' : '0')};
  padding-left: ${(props) => (props.marLeft ? '1.5em' : '0')};
  padding:0px 20px;
  cursor: pointer;
  height: 40px;
  
  
  ::before {
    border: 1px solid #cccccc;
    content: "";
    position: absolute;
    top: 0;
    right: 0;
    height: 40px;
    bottom: 0;
    left: 0;
    z-index: -1;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    ${(props) => props.bgColor ? `background-color:${props.bgColor};` : `background: ${props.status ? props.themeUi === "REGALBLAZE"
    ? globalStyles.chooseThemeColor[props.themeUi]?.color5
    : "transparent linear-gradient(74deg, #820F4C 0%, #BC3D81 100%) 0% 0% no-repeat padding-box" : 'white'};`}
    box-shadow: 0px 5px 25px #9d9d9d29;
    transform: scale(1.2, 1.3) perspective(1em) rotateX(2.5deg);
    transform-origin: bottom left;
  }
  `

export const SCTabHeader = styled.div`
  display: flex;
  width: 100%;
  align-items: center;
  overflow: hidden;
  margin-left: 2px;


  &::-webkit-scrollbar{
    width: 7px;
    height:5px;       
  }

  &::-webkit-scrollbar-track{
      border-radius: 30px;
      opacity: 1;
  }

  &::-webkit-scrollbar-thumb{
      width: 7px;
      /* UI Properties */
      background: #CBCBCB 0% 0% no-repeat padding-box;
      box-shadow: 0px 6px 9px #41414129;
      border-radius: 30px;
      opacity: 1;
  }
`
export const InputCheckBox = styled.input<{ theme: string }>`
    display:inline;
    width: 2em;
    height: 2rem;
    accent-color:${(props) => globalStyles.chooseThemeColor[props.theme].color5};
`

export const Wrapper = styled.div`
  width: 100%;
  height: 100%;
  padding: 0 16px;
  align-items: center;
  display: flex;
  flex-direction: column;
  & .sc-gazJty{
    padding: 0 !important;
    margin-top: -22px !important;
    font-size: 10px !important;
  }
 
  & > .ag-theme-alpine {
    margin: 0 20px 0;
    width: 100%;
    flex: 1;
  }
  & > button {
    width: max-content;
  }
  & > *:not(button, .toolbar-container) {
    transition: flex 0.2s ease-in-out !important;
  }
  & .toolbar-container {
    width: 100%;
    margin-bottom: 0;
    margin-top: 20px;
  }

  & .ag-header-cell-text {
    font-size: 12px;
  }
  & > .ag-theme-alpine{
      margin: 0 !important;
      }
  & div[data-testid="vf_pagination"]{
    margin: 0 !important;
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

export const ContentWrapper = styled.div`
  margin: 2rem 0 0 0;
`;

export const Text = styled.div`
  font-size: 14px;
  font-weight: 300;
`;

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
`;
