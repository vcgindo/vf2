import styled from "styled-components";
import * as gridSystem from "../../../styles/gridSystem";
import * as globalStyles from "../../../styles/global";

export const SCModalContent = styled.div`
  overflow-y: hidden;
  z-index: 10;
  position: fixed;
  top: 0px;
  right: 0px;
  bottom: 0px;
  left: 0px;
`;

export const SCModalBox = styled.div`
  display: flex;
  text-align: center;
  justify-content: center;
  align-items: center;
  min-height: 100%;
`;

export const SCWrapper = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  height: 454px;
`;

export const SCImg = styled.img`
  margin-bottom: 25px;
`;

export const SCTextAbove = styled.div`
  font-size: 2rem;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.6rem;
  }
`;

export const SCTextBelow = styled.div`
  font-size: 2rem;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.6rem;
  }
`;

export const SCBtnClose = styled.button<{colorTheme: string}>`
  font: normal normal 300 20px/26px Roboto;
  color: #ffffff;
  width: 222px;
  height: 46px;
  background: ${props => globalStyles.chooseThemeColor[props.colorTheme].colorButton};

  box-shadow: 0px 6px 25px #00000029;
  border-radius: 6px;
  margin: 20px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.6rem;
    width: 185px;
    height: 35px;
  }
`;

export const SCBtnBack = styled.div<{colorTheme: string}>`
  font: normal normal 300 18px/24px Roboto;
  color: ${ props => globalStyles.chooseThemeColor[props.colorTheme].color4};

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.6rem;
  }
`;
