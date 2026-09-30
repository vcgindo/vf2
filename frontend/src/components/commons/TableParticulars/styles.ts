import styled from "styled-components";
import * as globalStyles from "../../../styles/global";
import * as gridSystem from "../../../styles/gridSystem";

export const SCCount = styled.div<{ pathname: string }>`
  padding: ${(props) =>
    props.pathname === "/availability-comparison"
      ? "10px 10px 30px"
      : "0 10px"};

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding-bottom: 20px;
  }
`;

export const SCNavCount = styled.div<{ themeUi: string }>`
  background-color: ${(props) =>
    globalStyles.chooseThemeColor[props.themeUi].backGroundParticular};
  border-radius: 12px 12px 0 0;
  padding: 15px 25px 0 35px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding: 8px 12px 0 16px;
  }
`;
export const SCNavCountHeader = styled.div<{ themeUi: string }>`
  padding-bottom: 8px;
  padding-top: 8px;
  border-bottom: 1px dashed #929292;
  color: ${(props) =>
    props.themeUi === "CHARCOALCHIC"
      ? globalStyles.white
      : globalStyles.chooseThemeColor[props.themeUi]?.colorText};
  font-size: 1.5rem;
  display: flex;
  justify-content: space-between;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.2rem;
  }
`;

export const SCNavCountList = styled.ul`
  padding: 0;
  margin: 0;
`;
export const SCNavCountItem = styled.li<{ themeUi: string }>`
  display: flex;
  justify-content: space-between;
  font-size: 1.5rem;
  line-height: 21px;
  color: ${(props) =>
    props.themeUi === "CHARCOALCHIC"
      ? globalStyles.white
      : globalStyles.chooseThemeColor[props.themeUi]?.colorText};
  padding: 8px 0;
  list-style: none;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.2rem;
    padding: 4px 0;
  }
`;

export const SCNavCountFooter = styled.div<{
  themeUi: string;
}>`
  padding: 15px 25px 12px 35px;
  border-radius: 0 0 12px 12px;
  color: ${(props) =>
    props.themeUi === "CHARCOALCHIC" ? globalStyles.black : globalStyles.white};
  background-color: ${(props) =>
    globalStyles.chooseThemeColor[props.themeUi].footerParticular};
  font-size: 1.5rem;
  line-height: 21px;
  font-weight: 500;
  display: flex;
  justify-content: space-between;
  box-shadow: rgba(114, 114, 114, 0.16) 0px 3px 15px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding: 5px 12px 0 16px;
    font-size: 1.2rem;
  }

  #yield_particulars {
    box-shadow: 0px 3px 25px #77777729;
    background-color: #fff;
    color: #222;
    opacity: 1;
    position: fixed;
    width: 33vw;
    top: auto !important;

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      width: 38vw;
    }
  }

  .react-tooltip-arrow {
    left: 29px !important;
  }
`;

export const SCTotalValue = styled.div<{
  index: number;
  length: number;
  pathname: string;
}>`
  display: flex;
  white-space: nowrap;

  ${(props) => props.pathname === "/ist-forced-closure" && "width: 25vw;"}
  ${(props) => props.pathname === "/availability-comparison" && "width: 100%;"}

  ${(props) =>
    props.length === 3 &&
    props.index === 1 &&
    "width: 100%; justify-content: center;"}

  ${(props) =>
    props.length === 3 &&
    props.index === 2 &&
    "width: 100%;justify-content: end;"}
  align-items: center;
`;

export const BtnLeft = styled.img<{ pcs: boolean }>`
  ${(props) => !props.pcs && "transform: rotate(180deg); cursor: pointer;"}
  margin-right: 10px;
`;
export const BtnRight = styled.img<{ pcs: boolean }>`
  ${(props) => (!props.pcs ? "transform: rotate(180deg);" : "cursor: pointer;")}
`;
