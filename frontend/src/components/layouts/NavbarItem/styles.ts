import styled from "styled-components";
import * as globalStyles from "../../../styles/global";
import * as gridSystem from "../../../styles/gridSystem";

export const SCGridNav = styled.div<{ isHide: boolean; pathname: string }>`
  position: sticky;
  height: ${(props) =>
    props.pathname === "/availability-comparison" ? "" : "85vh"};
  top: 95px;
  max-height: 100%;
  z-index: ${(props) => (props.isHide ? "3" : "5")};
  display: flex;
  flex-direction: column;
  justify-content: space-between;

  @media (min-width: ${gridSystem.size.laptopL}) and (max-width: ${gridSystem
      .size.desktop}) {
    top: 70px;
  }

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    top: 95px;
  }

`;

export const SCNavLogoArea = styled.div`
  display: flex;
  margin-bottom: 5px;
`;

export const SCGridNavLogo = styled.img<{ isHide: boolean }>`
  width: 100%;
  max-width: 254px;
  height: 8rem;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    width: ${(props) => (props.isHide ? "100%" : "60%")};
    height: 9rem;
    padding-top: 16px;
  }

`;

export const SCNavIconHeader = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  width: 100%;

`;

export const SCNavIconNotifications = styled.img`
  padding: "0 calc(100% - 30vh)";
  width: 58px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    width: 40px;
    margin-top: 8px;
  }
`;

export const SCNavIconProfile = styled.div`
  height: 58px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    height: 40px;
    margin-top: 8px;
  }
`;

export const SCNavIconProfileImg = styled.img`
  cursor: "pointer";
  height: 58px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    height: 40px;
  }
  
`;

export const SCNavbar = styled.div`
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100%;
`;

export const SCProfile = styled.div<{ isHide: boolean }>`
  display: flex;
  justify-content: ${(props) => (props.isHide ? "center" : "space-between")};
  padding-bottom: 16px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding-bottom: 8px;
  }

`;

export const SCAvatar = styled.div`
  display: flex;
  align-items: center;

`;

export const SCAvatarImg = styled.img<{ isParentMenu: boolean }>`
  width: 68px;
  cursor: pointer;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    width: 42px;
  }
`;

export const SCIconMenu = styled.img<{ themeUi: string; isHide: boolean }>`
  position: absolute;
  right: -24px;
  width: 40px;
  z-index:300;
  border: ${(props) =>
    props.themeUi === "REGALBLAZE" ? "unset" : "5px solid #f9f9f9"};
  border-radius: 50%;
  cursor: pointer;
  margin-top: 20px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    width: 32px;
    margin-top: 0px;
    right: -17px;
  }

  transform: ${(props) => (props.isHide ? "rotate(180deg)" : "rotate(0)")};

`;

export const SCAvatarName = styled.div`
  font-size: 2rem;
  font-weight: 500;
  color: #333333;
  padding-left: 10px;
  position: relative;
  .arrow {
    position: absolute;
    top: 7px;
    right: -70px;
    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      top: 0px;
      right: -170px;
    }
  }
  .arrow::before,
  .arrow::after {
    position: relative;
    content: "";
    display: block;
    width: 9px;
    height: 1px;
    background: black;
    transition: 0.3s ease-in-out;
  }
  .arrow::before {
    transform: rotate(45deg);
  }
  .arrow::after {
    left: 6px;
    top: -1px;
    transform: rotate(-45deg);
  }
  .active {
    .arrow::before {
      transform: rotate(-45deg);
    }
    .arrow::after {
      transform: rotate(45deg);
    }
  }
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.6rem;
  }

`;
export const SCInterStore = styled.div<{ themeUi: string }>`
  color: ${(props) => globalStyles.chooseThemeColor[props.themeUi]?.colorText};
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    position: absolute;
    width: 200px;
  }
font-size:1.4rem;
`;

export const SCInterStoreArrowDown = styled.img<{ toggle: boolean }>`
  height: 8px;
  transform: ${(props) => (!props.toggle ? "rotate(0)" : "rotate(180deg)")};

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    height: 6px;
    left: 20rem;
    position: absolute;
  }
`;

export const SCNavMenu = styled.div`
  display: flex;
  align-items: center;
  gap: 6rem;
  padding-top: 20px;

  font-size: 1.5rem;
  font-weight: 300;
  color: #333333;
  padding-left: 10px;
  position: relative;
  .arrow {
    position: absolute;
    top: 7px;
    right: -70px;
    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      top: 0px;
      right: -170px;
      padding-top: 10px;
    }
  }
  .arrow::before,
  .arrow::after {
    position: relative;
    content: "";
    display: block;
    width: 9px;
    height: 1px;
    background: black;
    transition: 0.3s ease-in-out;
  }
  .arrow::before {
    transform: rotate(45deg);
  }
  .arrow::after {
    left: 6px;
    top: -1px;
    transform: rotate(-45deg);
  }
  .active {
    .arrow::before {
      transform: rotate(-45deg);
    }
    .arrow::after {
      transform: rotate(45deg);
    }
  }

  @media (min-width: ${gridSystem.size.laptopL}) and (max-width: ${gridSystem
    .size.desktop}) {
    padding-top: 5px;
  }

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.6rem;
    gap: 3rem;
    margin-bottom: 23px;
    padding-top: 20px;
  }
`;

export const SCNavName = styled.span`
  font-size: 1.8rem;
  font-weight: 500;
  color: ${globalStyles.black};
  padding-left: 10px;

`;

export const SCNavChild = styled.span<{ themeUi: string; active: boolean }>`
  padding-left: 10px;
  line-height: 24px;
  text-transform: capitalize;
  display: block;
  color: ${(props) =>
    props.active && props.themeUi === "CHARCOALCHIC"
      ? globalStyles.white
      : globalStyles.chooseThemeColor[props.themeUi]?.colorText};

  @media (min-width: ${gridSystem.size.laptopL}) and (max-width: ${gridSystem
      .size.desktop}) {
    padding-left: 8px;
    font-size: 1.4rem;
  }

`;

export const SCNavBox = styled.div`
  margin: 0 auto;
  display: flex;
  width: 100%;
  flex-direction: column;
  overflow:hidden overlay;
  &::-webkit-scrollbar{
    width: 7px;       
  }

  &::-webkit-scrollbar-track{
      border-radius: 30px;
      opacity: 1;
      background-color:#313132;
  }

  &::-webkit-scrollbar-thumb{
      width: 7px;
  /* UI Properties */
  background: gray 0% 0% no-repeat padding-box;
  box-shadow: 0px 6px 9px #41414129;
  border-radius: 30px;
  opacity: 1;
  }
`;

export const SCBoxTop = styled.div`
  display: flex;
`;

export const SCText = styled.div<{ themeUi: string }>`
  font-size: 2rem;
  font-weight: 300;
  color: ${(props) => globalStyles.chooseThemeColor[props.themeUi]?.colorText};
  padding: 20px 0 0 20px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding: 0px 0 0 15px;
    font-size: 1.6rem;
  }
`;

export const SCWrapMenu = styled.div`
  display: flex;
`;

export const SCNavList = styled.ul`
  padding-bottom: 20px;
  border-bottom: 3px solid #f9f9f9;
`;

export const SCNavItem = styled.li`
  display: flex;
  align-items: center;
  list-style: none;
  padding: 8px 0;
  cursor: pointer;
`;
export const SCCount = styled.div`
  padding: 0 10px;

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

  @media (min-width: ${gridSystem.size.laptopL}) and (max-width: ${gridSystem
    .size.desktop}) {
    padding: 15px 15px 0 15px;
  }

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding: 8px 12px 0 16px;
  }
`;
export const SCNavCountHeader = styled.div<{ themeUi: string }>`
  padding-bottom: 8px;
  border-bottom: 1px dashed #929292;
  color: ${(props) =>
    props.themeUi === "CHARCOALCHIC"
      ? globalStyles.white
      : globalStyles.chooseThemeColor[props.themeUi]?.colorText};
  font-size: 1.5rem;
  display: flex;
  /* border-bottom: 1px solid #; */
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

  &:last-child {
    border-top: 1px dashed #929292;
  }

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.2rem;
    padding: 4px 0;
  }
`;

export const SCNavCountFooter = styled.div<{
  bottomPosition: number;
  leftPosition: number;
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

  @media (min-width: ${gridSystem.size.laptopL}) and (max-width: ${gridSystem
    .size.desktop}) {
    padding: 5px 15px;
  }

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding: 5px 12px 0 16px;
    font-size: 1.2rem;
  }

  #yield_particulars {
    left: ${(props) => props.leftPosition}px !important;
    box-shadow: 0px 3px 25px #77777729;
    background-color: #fff;
    color: #222;
    opacity: 1;
    position: fixed;
    width: 33vw;
    bottom: ${(props) => props.bottomPosition}px !important;
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
export const SCBenefits = styled.p`
  margin-top: 5px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    margin-top: 0px;
  }
`;
export const SCSpace = styled.div`
  height: "300px";
  border-top: " 2px solid#EBF2F7";
  @media only screen and (max-height: 580px) {
    height: "150px";
  }
`;

export const SCIconTooltip = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    margin-top: 0px;
  }
`;

export const SCTableTooltip = styled.table`
  width: 100%;
  height: 33vh;
  border-collapse: collapse;
  overflow: hidden;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    height: 35vh;
  }
`;

export const SCTableTooltipTitle = styled.th`
  text-align: center;
  height: 5vh;

  :first-child {
    text-align: start;
  }
`;

export const SCNavLogout = styled.div<{ isHide: boolean }>`
  padding-top: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  ${(props) => (props.isHide ? "justify-content: center" : "")};
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding-top: 10px;
  }
`;
export const SCNavLogoutText = styled.span<{ isHide: boolean }>`
  font-size: 16px;
  font-weight: 300;
  letter-spacing: 1px;
  padding-left: 16px;
  color: #52575d;
  display: ${(props) => (props.isHide ? "none" : "")};
`;

export const SCMenu = styled.div``;

export const SCShowMenuItem = styled.div``;

export const SCMenuLeft = styled.div`
  padding: 5px 10px;
  border-radius: 10px;
  width: 100%;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding: 5px 5px;
  }
`;
export const SCMenuItem = styled.div<{
  active: true | false;
}>`
  color: ${(props) => (props.active ? "#0a58ca" : "#495057")};
  font-weight: 600;
  cursor: pointer;
`;
export const SCItemChild = styled.div<{
  active: true | false;
  status: true | false;
  themeUi: string;
}>`
  color: ${(props) => (props.active ? "#000000" : "#929292")};
  background-color: ${(props) =>
    props.active
      ? globalStyles.chooseThemeColor[props.themeUi].colorChooseItem
      : ""};
  width: 90%;
  white-space: nowrap;
  font-size: 1.8rem;
  font-weight: ${(props) => (props.active ? "500" : "300")};
  border-radius: ${(props) => (props.active ? "10px" : "")};
  overflow: hidden;
  transition: height 0.3s ease-in-out;
  height: ${(props) => (props.status ? "24px" : "0px")};
  margin: ${(props) => (props.status ? "12px 0px 12px 15px" : "0px")};
  padding: ${(props) => (props.status ? "18px 0px" : "unset")};
  display: flex;
  align-items: center;


 &:hover {
    transform: scale(1.05);
    transition: all 0.2s ease-in-out;
  }

  @media (min-width: ${gridSystem.size.laptopL}) and (max-width: ${gridSystem
    .size.desktop}) {
    margin: ${(props) => (props.status ? "5px 0px 5px 15px" : "0px")};
  }

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.2rem;
    margin: ${(props) => (props.status ? "2px 6px" : "0px")};
    padding: ${(props) => (props.status ? "13px 0px" : "unset")};
    width: ${(props) => (props.active ? "90%" : "100%")};
  }
`;
export const SCLogoutBtn = styled.div`
  font-weight: 600;
  cursor: pointer;
`;
export const SCInputIcon = styled.img`
  mask-size: cover;
  display: inline-block;
  height: 8px;
  margin-left: 10px;
  transform: rotate(-90deg);

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    height: 5px;
    margin-left: 5px;
  }
`;
