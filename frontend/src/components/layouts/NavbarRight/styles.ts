import styled from "styled-components";
import * as globalStyles from "../../../styles/global";

export const listColorTheme = [
  {
    title: "Noir Fusion",
    textColor: "NOIRFUSION",
    colorTheme: [
      globalStyles.NOIRFUSION.color1,
      globalStyles.NOIRFUSION.color2,
      globalStyles.NOIRFUSION.color3,
      globalStyles.NOIRFUSION.color4,
      globalStyles.NOIRFUSION.color5,
    ],
    status: false,
  },
  {
    title: "Pure Elegance",
    textColor: "PUREELEGANCE",
    colorTheme: [
      globalStyles.PUREELEGANCE.color1,
      globalStyles.PUREELEGANCE.color2,
      globalStyles.PUREELEGANCE.color3,
      globalStyles.PUREELEGANCE.color4,
      globalStyles.PUREELEGANCE.color5,
    ],
    status: false,
  },
  {
    title: "Charcoal Chic",
    textColor: "CHARCOALCHIC",
    colorTheme: [
      globalStyles.CHARCOALCHIC.color1,
      globalStyles.CHARCOALCHIC.color2,
      globalStyles.CHARCOALCHIC.color3,
      globalStyles.CHARCOALCHIC.color4,
      globalStyles.CHARCOALCHIC.color5,
    ],
    status: false,
  },
  {
    title: "Regal Blaze",
    textColor: "REGALBLAZE",
    colorTheme: [
      globalStyles.REGALBLAZE.color1,
      globalStyles.REGALBLAZE.color2,
      globalStyles.REGALBLAZE.color3,
      globalStyles.REGALBLAZE.color4,
      globalStyles.REGALBLAZE.color5,
    ],
    status: false,
  },
];

export const SCWrap = styled.div<{ isOpenNavbarRight: any }>`
  position: fixed;
  width: 477px;
  height: 100vh;
  right: ${(props) => (props.isOpenNavbarRight ? "0px" : "-500px")};
  justify-content: space-between;
  z-index: 9992;
  background-color: ${globalStyles.white};
  transition: ${globalStyles.customTransition};

`;

export const SCWrapTop = styled.div`
  display: flex;
  justify-content: space-between;
  height: 69px;
  padding: 20px;
  background-color: ${globalStyles.black};
  color: ${globalStyles.white};
  font-size: ${globalStyles.mainFontSize};
`;

export const SCWrapContent = styled.div`
  padding: 20px;
`;

export const SCTopText = styled.div``;

export const SCClose = styled.div`
  cursor: pointer;
`;

export const SCIconClose = styled.img``;

export const SCWrapItem = styled.div<{isActive:boolean}>`
  display: flex;
  font-size: 18px;
  margin-bottom:10px;
  align-items: center;
  padding: 15px 10px;
  transition:0.2s ease-in-out;
  border-radius:4px;
  background-color: ${(props)=>props.isActive ? '#cde3fa' : 'transparent'};
  outline:solid 2px ${(props)=>props.isActive ? ' rgb(153, 204, 255) ' : 'rgb(209,213,219)'};
  /* box-shadow: rgba(0, 0, 0, 0.05) 0px 0px 0px 1px, rgb(209, 213, 219) 0px 0px 0px 1px inset; */
  cursor:pointer;
  /* &:hover{
    background-color: #cde3fa;
    outline-color: rgb(153, 204, 255) ;
  } */
`;

export const SCWrapItemLeft = styled.div`
  display: flex;
  width: 170px;
  
`;

export const SCInputRadio = styled.input<{ themeUi: string }>`
  margin-bottom: 5px;
  margin-right:10px;
  cursor: pointer;

  &:checked {
    accent-color: ${(props) =>
      globalStyles.chooseThemeColor[props.themeUi]?.color5};
  }
`;

export const SCItemText = styled.span`
  width: 115px;
`;

export const SCListColor = styled.div`
  display: flex;
`;

export const SCColor = styled.div<{ color: string }>`
  background-color: ${(props) => props.color};
  width: 40px;
  height: 30px;
`;

export const SCButton = styled.button<{ themeUi: string }>`
  font: normal normal 300 16px/24px Roboto;
  padding: 10px 20px;
  border-radius: 6px;
  box-shadow: 0px 6px 25px #00000029;
  color: ${globalStyles.white};
  background: ${props => globalStyles?.chooseThemeColor[props.themeUi].colorButton};
`;
