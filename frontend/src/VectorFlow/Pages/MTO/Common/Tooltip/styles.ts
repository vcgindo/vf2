import styled from "styled-components";

export const TooltipTarget = styled.div`
  cursor: pointer;
`;

export const TooltipContainer = styled.div<{ $arrowLeft?: any, $myzoom?: any }>`
  color: white;
  background: #313131;
  border-radius: 4px;
  z-index: 10000;
  position: fixed;
  max-width: 300px;
  font-size: 16px;
  zoom: ${(props) => props.$myzoom ? props.$myzoom : 1};
  &:after {
    content: "";
    width: 0;
    height: 0;
    display: block;
    position: absolute;
    top: 99%;
    left: ${(props) => props?.$arrowLeft};
    transform: translateX(-50%);
    border-left: 10px solid transparent;
    border-right: 10px solid transparent;
    border-top: 10px solid #313131;
    border-bottom: 10px solid transparent;
  }
`;
