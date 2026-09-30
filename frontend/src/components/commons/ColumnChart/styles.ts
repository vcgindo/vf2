import styled from "styled-components";
import * as globalStyles from "../../../styles/global";
import * as gridSystem from "../../../styles/gridSystem";

const widthCol = "3vw";
const fontSize = "1.2rem";
const fontSizeResponsive = "0.9rem";

export const WrapperChart = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  text-align: center;
  margin: 10px 0 15px 70px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    margin: 10px 0 15px 55px;
  }
`;

export const ChartLeft = styled.div<{ themeUi: string }>`
  transform: rotate(-90deg);
  font-size: ${fontSize};
  color: ${(props) => globalStyles.chooseThemeColor[props.themeUi].colorText};
  position: relative;
  left: -47px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: ${fontSizeResponsive};
  }
`;

export const ChartRight = styled.div`
  display: flex;
  position: relative;
  width: 12vw;
  height: 25vh;
  border-left: 2px solid #d9d9d9;
  border-bottom: 2px solid #d9d9d9;
`;

export const WrapperColumnRed = styled.div<{ themeUi: string }>`
  display: flex;
  position: absolute;
  justify-content: center;
  align-items: center;
  background-color: #c9252b;
  border-left: 5px solid #dd3f3d;
  bottom: 0;
  left: 2vw;
  height: 10vh;
  width: ${widthCol};
  font-size: ${fontSize};
  color: ${globalStyles.white};

  &::before {
    content: "0";
    position: absolute;
    bottom: -6px;
    left: -3.5vw;
    color: ${(props) => globalStyles.chooseThemeColor[props.themeUi].colorText};
  }

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: ${fontSizeResponsive};
  }
`;

export const WrapperColumnGreen = styled.div<{ themeUi: string }>`
  display: flex;
  position: absolute;
  background-color: #096912;
  border-left: 5px solid #1e972a;
  justify-content: center;
  align-items: center;
  bottom: 10vh;
  left: 5vw;
  height: 8vh;
  width: ${widthCol};
  font-size: 1.2rem;
  color: ${globalStyles.white};

  &::before {
    content: "";
    position: absolute;
    background-color: #d9d9d9;
    width: 0.5vw;
    height: 0.2vh;
    bottom: 0px;
    left: -5.9vw;
  }

  &::after {
    content: "90%";
    position: absolute;
    bottom: -10px;
    left: -7.5vw;
    color: ${(props) => globalStyles.chooseThemeColor[props.themeUi].colorText};
    
    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      left: -7.7vw;
      bottom: -7px;
    }
  }

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 0.9rem;
  }
`;

export const WrapperColumnWhite = styled.div<{ themeUi: string }>`
  display: flex;
  position: absolute;
  // background-color: white;
  background: transparent linear-gradient(2deg, #f4f4f4 0%, #c1c1c1 100%) 0% 0%
    no-repeat padding-box;
  justify-content: center;
  align-items: center;
  bottom: 18vh;
  left: 8vw;
  height: 3vw;
  width: ${widthCol};
  font-size: 1.2rem;
  color: ${globalStyles.black};

  &::before {
    content: "";
    position: absolute;
    background-color: #d9d9d9;
    width: 0.5vw;
    height: 0.2vh;
    bottom: 0px;
    left: -8.6vw;
  }

  &::after {
    content: "110%";
    color: ${globalStyles.white};
    position: absolute;
    bottom: -10px;
    left: -10.5vw;
    color: ${(props) => globalStyles.chooseThemeColor[props.themeUi].colorText};

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      bottom: -7px;
      left: -10.7vw;
    }
  }

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 0.9rem;
  }
`;

export const TextColumn = styled.span`
  transform: rotate(-90deg);
  font-weight: 500;
`;
