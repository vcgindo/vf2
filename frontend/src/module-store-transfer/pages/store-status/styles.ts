import styled from 'styled-components'
import * as globalStyles from '../../../styles/global'
import * as GridSystem from '../../../styles/gridSystem'

export const SCQuickFiltersText = styled.p`
  font-size: 2rem;
  font-weight: 500;

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    font-size: 1.6rem;
  }
`

export const SCQuickFilterBox = styled.div`
  display: flex;
  // width: 100%;
  align-items: center;
  padding: 25px 0 0 20px;
`

export const SCQuickFilterFlex = styled.div`
  display: flex;
  position: sticky;
  top: 91px;
  z-index: 2;
  background-color: ${globalStyles.gray};

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    top: 73px;
  }
`

export const SCBoxHalfPart = styled.div`
  flex: 1 0 70%;
  box-shadow: 0px 10px 20px #c4c8d066;
  border-radius: 12px;
`

export const SCBoxFilter = styled.div`
  display: flex;
  column-gap: 20px;
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  height: 100%;

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    padding: 15px;
  }
`

export const SCProducFilterHeader = styled.div`
  display: flex;
  align-items: center;
  padding-bottom: 14px;
  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    padding-bottom: 8px;
  }
`

export const SCProductFilterImg = styled.img`
  width: 34px;
  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    width: 22px;
  }
`
export const SCProductFilterText = styled.p`
  font-size: 2rem;
  line-height: 2.6rem;
  font-weight: 500;
  padding-left: 18px;
  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    font-size: 1.6rem;
    line-height: 100%;
  }
`
export const SCButtonFilter = styled.div`
  padding-top: 30px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  flex: 1 0 10%;
  gap: 15px;
  text-align: center;
`
export const SCFilterBtn = styled.button<{themeUi: string}>`
  color: #fff;
  background-color: ${props => globalStyles.chooseThemeColor[props.themeUi]?.color5};
  padding: 8px 0px;
  font-size: 1.6rem;
  border-radius: 8px;
  width: 164px;
  /* font-weight: 500; */
  border: none;
  @media only screen and (max-width: 1490px) {
    width: 100px;
  }
`

export const SCResetFilterBtn = styled.button<{themeUi: string}>`
  color: ${props => globalStyles.chooseThemeColor[props.themeUi]?.color5};
  background-color: #fefefe;
  padding: 8px 0px;
  border-radius: 8px;
  font-weight: 500;
  width: 164px;
  border: 1px solid ${props => globalStyles.chooseThemeColor[props.themeUi]?.color5};
  @media only screen and (max-width: 1490px) {
    width: 100px;
  }
`

export const SCQuickFiltersDistance = styled.div`
  height: 30px;
  position: sticky;
  top: 242px;
  background-color: #f9f9f9;
  z-index: 1;

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    top: 214px;
  }
`

export const SCTextNoWrap = styled.span`
  white-space: nowrap;
`
