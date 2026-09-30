import styled from "styled-components";
import * as globalStyles from "../../../styles/global";
import * as gridSystem from "../../../styles/gridSystem";

export const SCTableBox = styled.div`
  background-color: ${globalStyles.white};
  border-radius: 12px;
  padding: 20px;
`;
export const SCTableInformation = styled.div`
  display: flex;
  align-items: center;
  padding-bottom: 20px;
`;

export const SCTableStyle = styled.div`
  padding-left: 16px;
  padding-right: 32px;
`;
export const SCTableStyleText = styled.p`
  font-size: 1rem;
  color: ${globalStyles.black};
`;
export const SCTableStyleTextSpan = styled.span`
  font-size: 1.2rem;
  color: ${globalStyles.black};
  font-weight: 500;
  max-width: 130px;
  display: block;
`;

export const SCTableList = styled.ul`
  display: flex;
  margin: 0;
  padding: 0;
`;

export const SCTableItem = styled.li`
  display: block;
  list-style: none;
  padding: 0 30px;
  border-left: 1px solid #f5f6fa;
  margin-bottom: 14px;
`;

export const SCTableItemName = styled.p`
  font-size: 1.4rem;
  color: ${globalStyles.black};
  font-weight: 300;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.1rem;
  }
`;

export const SCTableItemValue = styled.p`
  font-size: 1.6rem;
  color: ${globalStyles.black};
  font-weight: 500;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.2rem;
  }
`;

export const SCTableImages = styled.img`
  width: 100px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    width: 70px;
  }
`;

export const SCTableTab = styled.table`
  border: 1px solid #d8d8d8;
  border-collapse: collapse;
  border-radius: 6px;
`;

export const SCTableTr = styled.tr`
  text-align: left;
  :nth-child(even) {
    background-color: #f4f4f4;
  }
`;

export const SCTableTh = styled.th`
  padding: 6px 12px;
  font-size: 1.4rem;
  font-weight: 300;
  color: ${globalStyles.black};
  /* border: 1px solid #D8D8D8; */
  border-left: 1px solid #d8d8d8;
  border-collapse: collapse;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.2rem;
    padding: 0 4px;
  }
`;

export const SCTableCheckbox = styled.span`
  display: flex;
  align-items: center;
  margin-bottom: 4px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    height: 30px;
  }
  @media only screen and (max-width: 1629px) {
    height: 30px;
  }
`;

export const SCTableTd = styled.td`
  padding: 6px 12px;
  border-left: 1px solid #d8d8d8;
  font-size: 1.4rem;
  font-weight: 500;
  color: ${globalStyles.black};
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.2rem;
    padding: 0px 4px;
  }
`;
export const SCTableTdItem = styled.td`
  padding: 6px 12px;
  border-left: 1px solid #d8d8d8;
  font-size: 1.4rem;
  font-weight: 500;
  color: ${globalStyles.black};
  display: flex;
  align-items: center;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.2rem;
    padding: 0px 4px;
    width: 140px;
  }
`;

export const SCButtonChecBox = styled.div`
  display: flex;
  justify-content: flex-start;
  padding-top: 28px;
`;

export const SCWrapPvPA = styled.div`
  display: flex;
`;

export const SCValuePvPA = styled.span<{ value: string }>`
  min-width: 15px;
  ${(props) => props.value === "R" && "color: red"}
  ${(props) => props.value === "G" && "color: green"}
  ${(props) => props.value === "W" && "color: #848484"}
`;

export const SCLargerSign = styled.img`
  height: 20px;
  margin: 0 6px 0 2px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    margin: 0 6px 0 0px;
  }
`;

export const SCRupeeContainer = styled.div`
  display:inline-block;
`;

export const SCRupeeSign = styled.img`
  margin-left:4px;
  margin-right:3px;
`;
