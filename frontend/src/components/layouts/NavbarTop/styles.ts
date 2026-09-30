import styled from "styled-components";
import * as globalStyles from "../../../styles/global";
import * as gridSystem from "../../../styles/gridSystem";
import { Link } from "react-router-dom";

export const SCWrap = styled.div<{ colorTheme: string }>`
  display: flex;
  justify-content: space-between;
  padding: 20px;
  height: 100%;
  background: ${(props) =>
    globalStyles.chooseThemeColor[props.colorTheme]?.color1};
`;

export const SCLeft = styled.div`
  display: flex;
  align-items: center;
`;

export const SCRight = styled.div`
  display: flex;
  align-items: center;
  height: 100%;
`;

export const SCWrapLogo = styled.div``;

export const SCLogo = styled.img`
  height: 62px;
  margin: 0 10px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    height: 40px;
  }
`;

export const SCWrapBreadcrumb = styled.div``;

export const SCBreadCrumb = styled.div<{ colorTheme: string }>`
  color: ${(props) =>
    props.colorTheme === "PUREELEGANCE"
      ? globalStyles.chooseThemeColor[props.colorTheme]?.color3
      : globalStyles.white};
  font-size: ${globalStyles.mainFontSize};
  margin: 0 10px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: ${globalStyles.responsiveFontSize};
  }
`;

export const SCWrapImg = styled.div``;

export const SCImg = styled.img`
  height: 50px;
  width: 50px;
  margin: 0 10px;
  cursor: pointer;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    height: 30px;
    width: 30px;
    margin: 0 5px;
  }
`;

export const SCImgLink = styled(Link)`
  height: 50px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    height: 30px;
  }
`;

export const SCTxt = styled.span<{ colorTheme: string }>`
  width: 100px;
  font-size: ${globalStyles.mainFontSize};
  color: ${(props) =>
    props.colorTheme === "PUREELEGANCE"
      ? globalStyles.chooseThemeColor[props.colorTheme]?.color3
      : globalStyles.white};
  font-weight: 200;
  margin-left:10px;
    overflow: hidden; 
    text-overflow: ellipsis; 
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: ${globalStyles.responsiveFontSize};
    width: 80px;
  }
`;

export const SCVerticalPartitions = styled.div`
  min-width: 2px;
  background: #d8d8d8;
  height: 50px;
  margin: 0 5px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    height: 30px;
    min-width: 1px;
  }
`;
