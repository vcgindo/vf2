import styled from "styled-components";
import * as globalStyles from "../../../styles/global";
import * as gridSystem from "../../../styles/gridSystem";

export const SCBoxFilter = styled.div`
  display: flex;
  column-gap: 20px;
  background-color: ${globalStyles.white};
  box-shadow: 0px 10px 20px #c4c8d066;
  border-radius: 12px;
  padding: 20px;
  width: 100%;
  margin-bottom: 20px;
  @media only screen and (max-width: 1490px) {
    padding: 10px;
  }
`;
export const SCFilterBtn = styled.button<{themeUi: string}>`
  color: #fff;
  background-color: ${props => globalStyles.chooseThemeColor[props.themeUi]?.color5};
  padding: 8px 0px;
  font-size: 1.6rem;
  border-radius: 8px;
  width: 164px;
  /* font-weight: 500; */
  border: none;
  @media only screen and (max-width: 1490px) {
    width: 100px;
  }
`;

export const SCBoxFilterSticky = styled.div`
  position: sticky;
  top: 91px;
  z-index: 2;
  background-color: #f9f9f9;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    top: 69px;
  }
`;

export const SCResetFilterBtn = styled.button<{themeUi: string}>`
  color: ${props => globalStyles.chooseThemeColor[props.themeUi]?.color5};
  background-color: #fefefe;
  padding: 8px 0px;
  border-radius: 8px;
  font-weight: 500;
  width: 164px;
  border: 1px solid ${props => globalStyles.chooseThemeColor[props.themeUi]?.color5};
  @media only screen and (max-width: 1490px) {
    width: 100px;
  }
`;

export const SCButtonFilter = styled.div`
  padding-top: 48px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  flex: 1 0 10%;
  gap: 15px;
  text-align: center;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding-top: 30px;
  }
`;

export const SCQuickFilters = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 20px;
  background-color: #f9f9f9;
`;

export const SCQuickFiltersWrap = styled.div`
  display: flex;
  min-width: 85%;
  gap: 2rem;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.laptopL}) {
  gap: 1.5rem;
}
`

export const SCQuickAction = styled.div`
  background-color: ${globalStyles.white};
  display: flex;
  padding: 8px 20px;
  align-items: center;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding: 8px 10px;
  }
`;

export const SCQuickActionLabel = styled.label`
  font-size: 1rem;
  color: ${globalStyles.secondaryColor};
`;

export const SCQuickActionSelectInput = styled.select`
  font-weight: 500;
  font-family: "Roboto";
  font-size: 1.4rem;
  outline: none;
  border: none;
  padding-right: 50px;
`;

export const SCQuickActionSelect = styled.div`
  display: grid;
  padding-left: 30px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.desktop}) {
    padding-left: 6px;
  }
`;

export const SCQuickActionButton = styled.button`
  background-color: ${globalStyles.mainColor};
  height: 52px;
  width: 76px;
  border-radius: 6px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.desktop}) {
    width: 47px;
    height: 36px;
  }
`;

export const SCQuickFilterBox = styled.div`
  /* padding: 0 24px; */
  display: flex;
  align-items: center;
  // border-right: 2px solid #D8D8D8 ;
  // padding-right: 20px;
  /* @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.desktop}) {
    padding: 0 12px;
  } */
`;

export const SCQuickFiltersText = styled.p`
  font-size: 2rem;
  font-weight: 500;
  white-space: nowrap;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.desktop}) {
    font-size: 1.2rem;
  }
`;
