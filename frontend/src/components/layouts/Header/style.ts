import styled from "styled-components";
import * as globalStyles from "../../../styles/global";
import * as gridSystem from "../../../styles/gridSystem";
import { Link } from "react-router-dom";

export const SCHeaderBox = styled.div`
  display: flex;
  justify-content: space-between;
  padding-top: 30px;
  align-items: center;
  background-color: #f9f9f9;
`;

export const SCHeaderBoxIst = styled.div`
  display: flex;
  justify-content: space-between;
  background-color: ${globalStyles.white};
  margin-bottom: 40px;
  padding: 18px;
  border-radius: 0px 0px 0px 12px;
`;

export const SCHeaderText = styled.p`
  font-size: 2.6rem;
  font-weight: 500;
  color: ${globalStyles.black};
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.8rem;
  }
`;




export const SCHeaderContent = styled.div`
  display: flex;
  align-items: center;
`;

export const SCHeaderWelcome = styled.p`
  font-size: 2rem;
  color: ${globalStyles.black};
`;

export const SCHeaderName = styled.span`
  font-weight: 500;
  font-size: 2rem;
`;

export const SCHeaderSubTextIst = styled.span`
  color: #b4b4b4;
  font-size: 2rem;
`;

export const SCExportAllBox = styled.div`
  display: flex;
  justify-content: flex-end;
`;

export const SCExportAllBoxButton = styled.button`
  background-color: ${globalStyles.white};
  border: 1px solid #11b221;
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  align-items: center;
  width: 184px;
  height: 47px;
  display: flex;
  align-items: center;
  justify-content: center;
`;
export const SCExportAllBoxSpan = styled.span`
  color: #11b221;
  font-size: 1.2rem;
  font-weight: 600;
  padding: 0 10px;
`;

export const SCHeaderButtonIst = styled.span<{ themeUi: string }>`
  background: ${(props) =>
    props.themeUi === "REGALBLAZE"
      ? globalStyles.chooseThemeColor[props.themeUi]?.color5
      : "linear-gradient(180deg, #bc3d81 0%, #820f4c 100%)"};
  border-radius: 6px;
  cursor: pointer;
  font-size: 2rem;
  font-weight: 500;
  padding: 10px 40px;
  color: ${globalStyles.white};
  margin-left: 30px;
  height: 47px;
  width: 117px;
  display: flex;
  align-items: center;
  justify-content: center;
`;

export const SCHeaderButtonIstSaving = styled.span`
  background-color: #b4b4b4;
  border-radius: 6px;
  cursor: pointer;
  font-size: 2rem;
  font-weight: 500;
  padding: 10px 40px;
  color: ${globalStyles.white};
  margin-left: 30px;
  height: 47px;
  width: 117px;
  display: flex;
  align-items: center;
  justify-content: center;
`;
export const SCHeaderButtonIstDelete = styled.span`
  border: 1px solid #b4b4b4;
  border-radius: 6px;
  cursor: pointer;
  font-size: 2rem;
  font-weight: 500;
  padding: 10px 40px;
  color: #b4b4b4;
  margin-left: 30px;
  height: 47px;
  width: 117px;
  display: flex;
  align-items: center;
  justify-content: center;
`;

export const SCHeaderProfile = styled(Link)`
  height: 58px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 2.8rem;
    height: 45px;
  }
`;

export const SCHeaderIconNotifi = styled.img`
  padding: 0 20px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    height: 45px;
  }
`;

export const SCHeaderIconProfile = styled.img`
  width: 100%;
  height: 100%;
  cursor: pointer;
`;
export const SCWrapperImg = styled.div<{ isHideLogo: boolean}>`
  position: fixed;
  right: 0px;
  top:135px;
  width: ${(props) => (props.isHideLogo ? "fit-content" : "1vw")};;
  height: 55px;
  margin-top: -22px;
  box-shadow: 0px 6px 9px #00000029;
  border-radius: 6px 0px 0px 6px;
  background: #ffffff 0% 0% no-repeat padding-box;
  cursor: pointer;
  transition: ${globalStyles.customTransition};
  z-index:1000;
  gap:5px;
  `
export const ClientNameText = styled.div<{marginLeft:any, isHideLogo: boolean }>`
  flex: 1;
  white-space: nowrap;
  margin-left: ${props => props.marginLeft};
  overflow: hidden;
  text-overflow: ellipsis;
  // display: ${props => (props.isHideLogo ? 'none' : 'block')};
  z-index: 1000;
  font-size: 1.3rem;
  font-weight: 500;
  font-family:Roboto;
  padding-right:5px;        
`;

export const SCImg = styled.img<{marginLeft?:any, isHideLogo: boolean }>`
  height: 40px; // Example size
  // display: ${props => (props.isHideLogo ? 'none' : 'block')};
  z-index: 1000;
  margin-left: ${props => (props.marginLeft ? props.marginLeft : '')};
  padding-left:18px;
  padding-right:8px;
`;