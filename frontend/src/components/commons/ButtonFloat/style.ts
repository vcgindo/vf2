import styled from "styled-components";
import * as globalStyles from "../../../styles/global";

export const SCButtonFloat = styled.button<{ themeUi: string }>`
  border: none;
  width: 100%;
  height: 100%;
  color: ${globalStyles.white};
  background: ${(props) =>
    props.themeUi === "REGALBLAZE"
      ? globalStyles.chooseThemeColor[props.themeUi]?.color5
      : "transparent linear-gradient(180deg, #bc3d81 0%, #820f4c 100%) 0% 0% no-repeat padding-box"};
  font-size: 16px;
  border-radius: 6px;
  font-weight: 500;
  opacity: 1;
`;

export const SCImg = styled.img`
  padding-right: 10px;
`;
