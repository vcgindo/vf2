import styled from "styled-components";
import * as globalStyles from "../../../styles/global";
import * as GridSystem from "../../../styles/gridSystem";

export const SCManualBoxCenter = styled.div`
  @media (min-width: ${GridSystem.size.laptopL}) {
    margin-top: 10px;
    margin-left: 50px;
  }

  /* @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
    .size.laptopL}) {
    margin-top: 20px;
  } */
`;

export const SCManualBox = styled.div`
  width: 100%;
  background-color: ${globalStyles.white};
  border: 1px solid #d6d6d6;
  border-radius: 6px;
  padding: 82px 0 68px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    padding: 50px 0;
  }
  @media only screen and (max-height: 650px) {
    padding: 20px 0;
  }
`;

export const SCManualText = styled.p`
  font-size: 3.6rem;
  text-align: center;
  color: ${globalStyles.black};
  font-weight: 500;
  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    font-size: 3rem;
    font-weight: 500;
  }
`;

export const SCManualDrag = styled.div`
  box-shadow: 5px 5px 30px #6e6b6b29;

  border-radius: 6px;
  margin-top: 15px;
  margin-bottom: 30px;
  width: 100%;
  max-width: 778px;
  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    margin-top: 20px;
    margin-bottom: 20px;
  }
`;

export const SCManualExcel = styled.div`
  display: flex;
  justify-content: center;
`;

export const SCManualDragText = styled.p`
  margin: 15px 80px;
  font-size: 2.5rem;
  text-align: center;
  color: ${globalStyles.black};
  font-weight: 500;
`;
export const SCDragDrop = styled.div`
  display: "flex";
  justify-content: "center";
  align-items: "center";
  padding: 20px 0;
`;

export const SCManualDowload = styled.div`
  padding-top: 20px;
  display: flex;
  justify-content: center;
  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    /* padding-top: 20px; */
  }
  @media only screen and (max-height: 580px) {
    padding-top: 10px;
  }
`;

export const SCManualDowloadText = styled.p`
  font-size: 1.8rem;
  padding-bottom: 30px;
  padding-right: 10px;
  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    padding-bottom: 20px;
  }
  @media only screen and (max-height: 580px) {
    padding-bottom: 10px;
  }
`;

export const SCManualUpload = styled.div`
  display: flex;
  align-items: center;
`;

export const SCManualUploadButton = styled.button`
  box-shadow: 2px 2px 15px #a2a0a029;
  border-radius: 0px 0px 0px 6px;
  width: 162px;
  height: 50px;
  color: ${globalStyles.white};
  background-color: ${globalStyles.black};
`;

export const SCManualUploadText = styled.p`
  color: #c8c5c5;
  font-size: 1.8rem;
  padding-left: 30px;
`;
export const SCManualUploadInput = styled.input`
  /* border: 0;
    clip: rect(0 0 0 0);
    height: 1px;
    margin: -1px;
    overflow: hidden;
    padding: 0;
    position: absolute;
    width: 1px; */
`;

export const SCManualUploadBtn = styled.button<{ themeUi: string,disabled?:boolean }>`
  background:
    ${(props) =>
      props.disabled
      ?
      "gray"
      :
      props.themeUi === "REGALBLAZE"
        ? globalStyles.chooseThemeColor[props.themeUi]?.color5
        : "transparent linear-gradient(180deg, #bc3d81 0%, #820f4c 100%)"};
  border-radius: 6px;
  font-size: 2.2rem;
  color: ${globalStyles.white};
  padding: 10px 40px;
  border: none;
`;

export const SCManualImgUpload = styled.img`
  padding-right: 12px;
`;
