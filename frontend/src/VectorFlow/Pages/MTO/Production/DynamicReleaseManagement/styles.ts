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