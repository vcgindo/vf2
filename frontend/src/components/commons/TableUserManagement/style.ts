import styled from 'styled-components'
import * as globalStyles from '../../../styles/global'
import * as GridSystem from '../../../styles/gridSystem'

export const SCTableBox = styled.div`
  background-color: ${globalStyles.white};
  border-radius: 12px;
  box-shadow: 0px 10px 20px #c4c8d066;
  max-height: 550px;
  overflow-y: auto;

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    max-height: 380px;
  }
`
export const SCTableInformation = styled.div`
  display: flex;
  align-items: center;
  padding-bottom: 20px;
`

export const SCTableStyle = styled.div`
  padding-left: 16px;
  padding-right: 32px;
`
export const SCTableStyleText = styled.p`
  font-size: 1rem;
  color: ${globalStyles.black};
`
export const SCTableStyleTextSpan = styled.span`
  font-size: 1.2rem;
  color: ${globalStyles.black};
  font-weight: 500;
  max-width: 130px;
  display: block;
`

export const SCTableList = styled.ul`
  display: flex;
  margin: 0;
  padding: 0;
`

export const SCTableItem = styled.li`
  display: block;
  list-style: none;
  padding: 0 30px;
  border-left: 1px solid #f5f6fa;
`

export const SCTableItemName = styled.p`
  font-size: 1.4rem;
  color: ${globalStyles.black};
  font-weight: 300;
`

export const SCTableItemValue = styled.p`
  font-size: 1.6rem;
  color: ${globalStyles.black};
  font-weight: 500;
`

export const SCTableTab = styled.table`
  border-collapse: collapse;
  border-radius: 6px;
`

export const SCTableTbody = styled.tbody`
  :nth-child(even) {
    background-color: ${globalStyles.backgroundRowTable};
  }
`

export const SCTableTr = styled.tr`
  text-align: left;
  position: sticky;
  top: -1px;
  z-index: 1;
  background: white;
`

export const SCTableTh = styled.th`
  padding: 14px 10px;
  font-size: 2rem;
  font-weight: 500;
  color: ${globalStyles.black};
  // border-left: 1px solid #D8D8D8;
  border-collapse: collapse;

  :first-child {
    padding-left: 50px;
  }

  :last-child {
    padding-right: 50px;
  }

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    font-size: 1.6rem;
  }
`

export const SCTableTitle = styled.div`
  border-right: 1px solid #d8d8d8;
  padding-right: 10px;
`

export const SCTableCheckbox = styled.span`
  padding-right: 10px;
`

export const SCTableTd = styled.td`
  padding: 6px 10px 0;
  font-size: 1.4rem;
  font-weight: 500;
  color: ${globalStyles.black};

  :first-child {
    padding-left: 50px;
  }

  :nth-child(4) {
    white-space: nowrap;
  }
`

export const SCTableTdCenter = styled.td`
  display: flex;
  justify-content: center;
  padding: 6px 12px;
  font-size: 1.4rem;
  font-weight: 500;
  color: ${globalStyles.black};
  padding-right: 50px;
`

export const SCButtonChecBox = styled.div`
  display: flex;
  justify-content: flex-start;
  padding-top: 28px;
`

export const SCTableTrValue = styled.tr`
  border-top: 1px solid #d8d8d8;
  :nth-child(even) {
    background-color: ${globalStyles.backgroundRowTable};
  }
`

export const SCIconWrapper = styled.div`
    display :inline-block;
    position: relative;
    cursor: pointer;

    .user-manage-tooltip{
      z-index:1;
    }
    `;

export const SCIcon = styled.img`
  .circle {
    fill: red;
  }
`
