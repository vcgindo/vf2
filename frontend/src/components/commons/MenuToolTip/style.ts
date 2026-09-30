import styled from "styled-components";
import * as globalStyles from "../../../styles/global";
import * as gridSystem from "../../../styles/gridSystem";

export const WrapToolTip = styled.div<{left?: number}>`
  .tooltip_list {
    pointer-events: auto;
    background: ${globalStyles.white};
    top: 0 !important;
    left: ${props => props?.left}px !important;
    opacity: 1;
    z-index: 900000;
    // visibility: hidden;
    // transition: 100ms visibility ease-in;
    &.react-tooltip__show {
      visibility: visible;
    }
  }
`;


export const TooltipContainer = styled.div`
  color: ${globalStyles.black};
  text-align: left;
  cursor: pointer;
  // max-height:300px;
  max-height: ${props => props.style?.maxHeight || "200px"};
  overflow:hidden;
    // min-width: 300px;
    position: absolute;
    margin-left:-16px;
    border-radius:5px !important;

  @media (min-width: ${gridSystem
    .size.desktop}) {
    max-height:550px;
  }
`;

export const TooltipTitle = styled.div`
  font-size: 1.8rem;
  border-bottom: 1px solid #929292;
   position: sticky;
  padding: 8px 10px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.laptopL}) {
    font-size: 1.2rem;
    padding: 4px 10px;
  }
`;

export const TooltipContent = styled.div<{ action: boolean; themeUi: string }>`
  display: flex;
  align-items: center;
  font-size: 1.8rem;
  padding: 6px 10px;
  font-weight: ${(props) => (props.action ? 500 : 300)};
  margin: 5px 0;
  border-radius: 5px;
  color: ${(props) =>
    props.action
      ? globalStyles.chooseThemeColor[props.themeUi].textColorActiveTooltip
      : "unset"};
  background-color: ${(props) =>
    props.action
      ? globalStyles.chooseThemeColor[props.themeUi].backgroundActiveTooltip
      : "unset"};
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.laptopL}) {
    font-size: 1.2rem;
    margin: 0;
  }

  &:hover {
    background-color: #f1f1f1;
  }
`;

export const SCIcon = styled.img<{ src: string }>`
  margin: 0 0 2px 5px;
  ${(props) =>
    props.src === "/assets/img/nav/arrow_down.svg" &&
    "transform: rotate(-90deg);"}
`;

export const TooltipTrigger = styled.div``;
