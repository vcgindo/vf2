import styled from "styled-components";
import * as globalStyles from "../../../styles/global";

export const SwapperText = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 1.6rem;
  margin-bottom: 10px;
`;

export const TextInPage = styled.span``;

export const TextAllPage = styled.span<{themeUi: string}>`
  padding: 10px;
  color: ${props => globalStyles.chooseThemeColor[props.themeUi].color5};
  cursor: pointer;
  font-weight: 500;
  border-radius: 5px;
  transition: ${globalStyles.customTransition};

  &:hover {
    background-color: #f1f1f1;
  }
`;
