import styled from "styled-components";
import * as globalStyles from "../../../styles/global";
import * as gridSystem from "../../../styles/gridSystem";

export const SCWrapper = styled.div`
  height: 50%;
  display: flex;
  justify-content: center;
  flex-direction: column;
  align-items: center;
  position: relative;
  top: 10px;
`;

export const SCInput = styled.input<{ colorTheme: string }>`
  -webkit-appearance: none;
  appearance: none;
  height: 40px;
  width: 90px;
  background-color: ${globalStyles.white};
  -webkit-border-radius: 25px;
  border-radius: 25px;
  padding: 0 2px;
  margin: 0;
  cursor: pointer;
  border: 1px solid
    ${(props) => globalStyles.chooseThemeColor[props.colorTheme]?.color5};

  &::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 32px;
    height: 32px;
    background-color: ${(props) =>
      globalStyles.chooseThemeColor[props.colorTheme]?.color5};
    border-radius: 50%;
    cursor: pointer;

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      width: 25px;
      height: 25px;
    }
  }

  &:focus {
    outline: none;
  }

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    width: 70px;
    height: 30px;
  }
`;

export const SCText = styled.span`
  font-size: 1.4rem;
  color: ${globalStyles.black};
  font-weight: 300;
`;
