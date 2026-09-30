import styled from "styled-components";
import * as gridSystem from "../../../../../../styles/gridSystem";

export const NoteWrapper = styled.div`
  margin-top: 20px;
  display: flex;
  align-items: center;
  gap: 20px;
  width: 50%;
  border-radius: 4px;
  background-color: #ebebeb;
  color: #4a4a4a;
  padding: 10px;

  @media only screen and (min-width: ${gridSystem.size
      .mobileS}) and (max-width: ${gridSystem.size.mobileL}) {
    margin-top: 40px;
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    border-radius: 4px;
    background-color: #ebebeb;
    color: #4a4a4a;
    padding: 5px;
  }
`;

export const LogoWrapper = styled.div`
  padding: 10px;
`;
