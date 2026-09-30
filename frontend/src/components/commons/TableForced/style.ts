import styled from 'styled-components'
import * as globalStyles from '../../../styles/global'
import * as gridSystem from '../../../styles/gridSystem'

export const SCTableBox = styled.div`
  background-color: ${globalStyles.white};
  border-radius: 12px;
  padding: 20px;
`
export const SCTableInformation = styled.div`
  display: flex;
  align-items: center;
  padding-bottom: 20px;
  justify-content: space-between;
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
  &:nth-child(1) {
    padding-left: 0;
    border: unset;
  }
`

export const SCTableItemName = styled.p`
  font-size: 1.4rem;
  color: ${globalStyles.black};
  font-weight: 300;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.2rem;
  }
`

export const SCTableItemValue = styled.p`
  font-size: 1.6rem;
  color: ${globalStyles.black};
  font-weight: 500;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.4rem;
  }
`

export const SCTableTab = styled.table`
  border: 1px solid #d8d8d8;
  border-collapse: collapse;
  border-radius: 6px;
`

export const SCTableTr = styled.tr`
  text-align: left;
  :nth-child(even) {
    background-color: #f4f4f4;
  }
`

export const SCTableTh = styled.th`
  padding: 6px 12px;
  font-size: 1.4rem;
  font-weight: 300;
  color: ${globalStyles.black};
  border: 1px solid #d8d8d8;
  border-collapse: collapse;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding: 6px;
    font-size: 1.2rem;
  }
`
export const SCTableThItem = styled.th`
  padding: 6px 12px;
  font-size: 1.4rem;
  width: 80px;
  font-weight: 300;
  color: ${globalStyles.black};
  border: 1px solid #d8d8d8;
  border-collapse: collapse;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding: 6px;
    font-size: 1.2rem;
  }
`

export const SCTableCheckbox = styled.span`
  position: relative;
  top: -3px;
`

export const SCTableTd = styled.td`
  padding: 6px 12px;
  border-left: 1px solid #d8d8d8;
  font-size: 1.4rem;
  font-weight: 500;
  /* width: 20px; */
  color: ${globalStyles.black};
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding: 6px;
    font-size: 1.2rem;
  }
`
export const SCTableTdDay = styled.td`
  padding: 6px 12px;
  border-left: 1px solid #d8d8d8;
  font-size: 1.4rem;
  font-weight: 500;
  color: ${globalStyles.black};
  width: 98px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding: 6px;
    width: 90px;
    font-size: 1.2rem;
  }
`

export const SCButtonChecBox = styled.div`
  display: flex;
  justify-content: flex-end;
  padding-top: 28px;
`

export const SCButtonContact = styled.button<{themeUi: string}>`
  display: flex;
  justify-content: flex-end;
  align-items: center;
  border-radius: 6px;
  border: 1px solid ${props => globalStyles.chooseThemeColor[props.themeUi]?.color5};
  background-color: ${globalStyles.white};
  padding: 10px 20px;
  color: ${props => globalStyles.chooseThemeColor[props.themeUi]?.color5};
  text-transform: uppercase;
  font-weight: 500;
  font-family: "Roboto";
`
export const SCImgContact = styled.img`
  margin-right: 6px;
`

export const SCTextStyle = styled.span`
  position: relative;
  top: 1px;
`
