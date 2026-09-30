import styled from "styled-components";
import * as globalStyles from "../../../styles/global";
import * as GridSystem from "../../../styles/gridSystem";

export const SCBoxFilterSticky = styled.div`
  position: sticky;
  top: 91px;
  z-index: 2;
  background-color: #f9f9f9;
  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    top: 69px;
  }
`;

export const SCBoxFilter = styled.div`
  display: flex;
  column-gap: 20px;
  background-color: ${globalStyles.white};
  box-shadow: 0px 10px 20px #c4c8d066;
  border-radius: 12px;
  padding: 20px;
  width: 100%;
  margin-bottom: 20px;
`;

export const SCSearchText = styled.div`
  position: relative;
  width: 155px;
  input {
    width: 100%;
    height: 46px;
    padding: 15px;
    box-sizing: border-box;
    padding-left: 30px;
    border-radius: 6px;
    border: 1px solid #929292;
    color: #929292;
    font-size: 1.2rem;
    outline: none;
    @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
        .size.laptopL}) {
      font-size: 9.8px;
      height: 36px;
      padding: 10px 4px 10px 28px;
    }
  }
  input[type="date"]::-webkit-calendar-picker-indicator {
    color: #d8d8d8;
    opacity: 1;
    display: block;
    /* background: url(https://mywildalberta.ca/images/GFX-MWA-Parks-Reservations.png) no-repeat; */
    width: 16px;
    height: 16px;
    border-width: thin;
    position: absolute;
    left: 4px;
  }
  img {
    position: absolute;
    left: 0px;
    top: 5px;
    padding: 10px;
    color: #f9f9f9;
    width: 35px;
    height: 35px;
    @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
        .size.laptopL}) {
      top: 0px;
    }
  }
  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    max-width: 120px;
  }
`;

export const SCResetFilterBtn = styled.button<{ themeUi: string }>`
  color: ${(props) => globalStyles.chooseThemeColor[props.themeUi]?.color5};
  background-color: #fefefe;
  padding: 8px 0px;
  border-radius: 8px;
  font-weight: 500;
  width: 164px;
  border: 1px solid
    ${(props) => globalStyles.chooseThemeColor[props.themeUi]?.color5};
  @media only screen and (max-width: 1490px) {
    width: 100px;
  }
`;

export const SCFilterBtn = styled.button<{ themeUi: string }>`
  color: #fff;
  background-color: ${(props) =>
    globalStyles.chooseThemeColor[props.themeUi]?.color5};
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

export const SCButtonFilter = styled.div`
  padding-top: 47px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  flex: 1 0 10%;
  gap: 15px;
  text-align: center;

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    padding-top: 32px;
  }
`;

export const SCQuickFilters = styled.div`
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: nowrap;
  padding-bottom: 20px;
`;

export const SCQuickFiltersWrap = styled.div`
  display: flex;
  min-width: 75%;
  gap: 2rem;
  align-items: flex-end;

  @media (max-width: ${GridSystem.size.desktop}) {
    gap: 0rem;
  }

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
    .size.laptopL}) {
  gap: 0.5rem;
}
`;

export const SCBoxFilterButton = styled.div`
`;

export const SCBoxFilterButtonLabel = styled.p`
  font-size: 1.5rem;
  color: #000;
  margin-bottom: 12px;
  margin-left: 10px;
  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.desktop}) {
    margin-left: 4px;
  }
`;

export const SCBoxFilterButtonFlex = styled.div`
  display: flex;
  align-items: center;
`;

export const SCExportAllBox = styled.div`
  display: flex;
  justify-content: flex-end;
  margin-top: 40px;
`;

export const SCExportAllBoxButton = styled.button`
  background-color: ${globalStyles.white};
  border: 1px solid #11b221;
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  align-items: center;

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    padding: 4px 10px;
  }
`;

export const SCExportAllBoxSpan = styled.span`
  color: #11b221;
  font-size: 1.3rem;
  font-weight: 500;
  padding: 0 10px;
  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    font-size: 11px;
  }
`;

export const SCIconLocation = styled.img`
  position: relative;
  top: 35px;
  max-width: 16px;
  left: 8px;
  z-index: 2;
`;
