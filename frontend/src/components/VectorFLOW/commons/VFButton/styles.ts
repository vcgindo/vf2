import styled from 'styled-components'
import * as globalStyles from "../../../../styles/global";

export const SCButton = styled.button<{ themeUi: string, isDisabled:boolean | undefined, customWidth:number | undefined}>`
  background:
    ${(props) =>
      props.themeUi === "REGALBLAZE"
        // ? globalStyles.chooseThemeColor[props.themeUi]?.color5
        ? "transparent linear-gradient(261deg, #FCA311 0%, #CB830E 100%) 0% 0% no-repeat padding-box"
        : "transparent linear-gradient(74deg, #820F4C 0%, #BC3D81 100%) 0% 0% no-repeat padding-box"};
  width:${(props)=>props.customWidth ? props.customWidth : 130}px;
  height:50px;
  border-radius: 6px;
  font-size:16px;
  font-family:'Roboto';
  letter-spacing:0px;
  font-weight:300;
  color: ${globalStyles.white};
  // padding: 15px 7px;
  border: none;
  box-shadow: -5px 4px 10px #919191B3;
  opacity:${(props)=>props.isDisabled ? 0.2 : 1};
  pointer-events:${(props) => props.isDisabled ? 'none' : 'all'};
  
  &:hover {
    transform: scale(1.01);
    transition: all 0.2s ease-in-out;
  }

   &:active {
    transform: scale(1.04) translateY(0.1px);
  }
`;

export const TooltipText = styled.div`
    padding: 8px 8px !important;
`;
