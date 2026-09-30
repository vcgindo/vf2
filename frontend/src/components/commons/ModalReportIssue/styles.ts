import styled from "styled-components";
import * as gridSystem from "../../../styles/gridSystem";
import * as globalStyles from "../../../styles/global";

export const SCModalContent = styled.div`
  overflow-y: hidden;
  z-index: 10;
  position: fixed;
  top: 0px;
  right: 0px;
  bottom: 0px;
  left: 0px;
`;

export const SCTextTitle = styled.span`
  display: flex;
  justify-content: center;
  width: 100%;
`;

export const SCCloseModal = styled.span`
  font-weight: 300;
  font-size: 2.6rem;
`;

export const SCWrapperContent = styled.div`
  padding: 0 74px;
  text-align: left;
  border-bottom: 0.5px dashed #707070;
`;

export const SCItem = styled.div``;

export const SCText = styled.label`
  display: block;
  font-size: 2rem;
  font-weight: 500;
  margin: 10px 0;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.6rem;
  }
`;

export const SCTextThin = styled.span`
  display: block;
  font-size: 2rem;
  font-weight: 300;
  margin: 10px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.6rem;
  }
`;

export const SCTextarea = styled.textarea`
  margin: 0;
  width: 100%;
  outline: none;
  border: none;
  height: 127px;
  border-radius: 6px;
  background: #ffffff 0% 0% no-repeat padding-box;
  opacity: 1;
  padding: 10px 15px;
  border: 0.30000001192092896px solid #707070;
  resize: unset;
  font: normal normal 300 20px/26px Roboto;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    height: 85px;
    font-size: 1.6rem;
  }
`;

export const SCWrapperText = styled.div`
  display: flex;
  font-size: 2rem;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.6rem;
  }
`;

export const SCWrapperImg = styled.div`
  margin-bottom: 20px;
`;

export const SCFileUploader = {
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  height: "100px",
  border: "0.5px dashed #707070",
  borderRadius: "4px",
  cursor: "pointer",
};

export const SCImg = styled.img``;

export const SCPlaceholderImg = styled.span`
  color: #7c7c7c;
  font-size: 1.6rem;
  margin-left: 10px;
  white-space: nowrap;
  text-overflow: ellipsis;
  max-width: 50%;
  overflow: hidden;
`;

export const SCModalBottom = styled.div`
  padding: 0 50px;
  text-align: right;
  margin: 30px 0;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    margin: 13px 0;
  }
`;

export const SCButtonGoBack = styled.button`
  width: 222px;
  height: 46px;
  box-shadow: 0px 6px 25px #00000029;
  border-radius: 6px;
  border: 1px solid #707070;
  font-size: 2rem;
  color: #313131;
  letter-spacing: 0px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    width: 170px;
    height: 35px;
    font-size: 1.6rem;
  }
`;

export const SCButtonSubmit = styled.button<{ themeUi: string }>`
  width: 222px;
  height: 46px;
  background: ${(props) =>
    globalStyles.chooseThemeColor[props.themeUi].colorButton};
  box-shadow: 0px 6px 25px #00000029;
  border-radius: 6px;
  font-size: 2rem;
  color: #ffffff;
  margin-left: 20px;
  font: normal normal 300 20px/26px Roboto;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    width: 170px;
    height: 35px;
    font-size: 1.6rem;
  }
`;

export const SCWrapperContentImg = styled.div`
  display: flex;
  margin-top: 10px;
  overflow-x: auto;
  white-space: nowrap;
`;

export const SCWrapperItemImg = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 114px;
  height: 39px;
  background: ${globalStyles.white};
  border: 0.5px solid #707070;
  border-radius: 4px;
  font-size: 1.6rem;
  margin-right: 10px;
  color: #7c7c7c;
`;

export const SCItemText = styled.span`
  margin-left: 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

export const SCItemImg = styled.img`
  margin: 0 10px;
`;
