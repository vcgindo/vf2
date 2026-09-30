import styled from "styled-components";
import * as gridSystem from "../../../styles/gridSystem";

export const SCVerticalPartitions = styled.div<{ height: string }>`
  min-width: 2px;
  background: #d8d8d8;
  height: ${(props) => props.height};
  margin: 0 5px;

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${
  gridSystem.size.laptopL
}) {
      height: 42px;

`;
