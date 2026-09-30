import styled from 'styled-components'
import * as globalStyles from "../../../../styles/global";

function getColor(props:any) {
  if(props.isDisabled){
    return '#9A9A9A'
  }
  if(props.color){
    return props.color
  }
  

  if(props.themeUi === "REGALBLAZE")
  {
    return globalStyles.chooseThemeColor[props.themeUi]?.color5;
    
  }

  return "transparent linear-gradient(74deg, #820F4C 0%, #BC3D81 100%) 0% 0% no-repeat padding-box";
  
}

function getBorderAndTextColor(props:any) {
  if(props.isDisabled){
    return '#9A9A9A'
  }
  if(props.color){
    return props.color
  }
  return globalStyles.chooseThemeColor[props.themeUi]?.color5;
}



export const SCButtonOutline = styled.button<{themeUi: string, isDisabled:boolean | undefined, hoverState:boolean, customWidth:number | undefined, color:string | undefined}>`
  color: ${props => getBorderAndTextColor(props)};
  background:#fefefe ;
  // background:${(props)=>getColor(props)} ;
  // padding: 15px 7px;
  border-radius: 6px;
  font-size:16px;
  font-family:'Roboto';
  letter-spacing:0px;
  font-weight:300;
  width:${(props)=>props.customWidth ? props.customWidth : 130}px;
  height:50px;
  // box-shadow: 0px 6px 25px #00000029;
  box-shadow: -5px 5px 10px #71717129;
  border: 1px solid ${props => getBorderAndTextColor(props)};
  pointer-events:${(props)=>props.isDisabled ? 'none' : 'all'};
  // &:hover{
  //   background:${(props)=>(!props.color) ? getColor(props) :props.color };
  //   color:white;
  
  &:hover {
    transform: scale(1.01);
    transition: all 0.2s ease-in-out;
  }
   &:active {
    transform: scale(1.04) translateY(0.1px);
  }
`


