import styled from "styled-components";
import * as globalStyles from "../../../styles/global";
import * as gridSystem from "../../../styles/gridSystem";

export const SCGridNav = styled.div`
  position: sticky;
  height: 85vh;
  top: 95px;
  max-height: 100%;
  z-index: 4;
  display: flex;
  flex-direction: column;
  justify-content: space-between;

`;

export const SCNavbar = styled.div``;

export const SCNavMenu = styled.div`
  padding: 15px 0;
  position: relative;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding: 7px 0;
  }

`;

export const SCNavIcon = styled.img<{widthIcon: string}>`
  width: ${props => props.widthIcon ? props.widthIcon : '24px' };

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
        width: ${props => props.widthIcon ? '25px' : '19px' };
  }

`;

export const SCNavBox = styled.div`
  margin: 0 auto;
  width: 100%;
  text-align: center;
  margin-top: 70px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    margin-top: 35px;
  }

`;

export const SCNavLogout = styled.div`
  padding-top: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-top: 1px solid #d8d8d8;
  margin: 0 6px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding: 10px 0 20px 0;
  }

  .logout-tooltip{
    font-weight: 500;
    font-family: Roboto;
    font-size: 1.2rem;
  }

`;

export const SCIconLogout = styled.img`
  width: 24px;
  height: 24px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.laptopL}) {
      width: 19px;
      height: 19px;
}
`;

export const SCMenu = styled.div``;

export const SCMenuItem = styled.div<{
  active: true | false;
  themeUi: string
}>`
  color: ${(props) => (props.active ? "#0a58ca" : "#495057")};
  font-weight: 600;
  cursor: pointer;
  background-color: ${(props) => (props.active ? globalStyles.chooseThemeColor[props.themeUi]?.color2 : "")};
  border-left: ${(props) => (props.active ? '5px solid' + globalStyles.chooseThemeColor[props.themeUi]?.color5 : "unset")};


   &:hover {
    transform: scale(1.02);
    transition: all 0.2s ease-in-out;
  }
`;
