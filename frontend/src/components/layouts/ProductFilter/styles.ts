import styled from 'styled-components'
import * as globalStyles from '../../../styles/global'
import * as gridSystem from '../../../styles/gridSystem'

export const SCProductFilter = styled.div`
  background-color: ${globalStyles.white};
  flex: 1 0 32%;
  width: 100%;
  padding-right: 20px;
  border-right: 1px solid #d8d8d8;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding-right: 12px;
  }
`

export const SCProductFilterText = styled.p`
  font-size: 2rem;
  line-height: 2.6rem;
  font-weight: 500;
  padding-left: 18px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    font-size: 1.6rem;
    line-height: 100%;
  }
`

export const SCProductFilterHeader = styled.div`
  display: flex;
  align-items: center;
  padding-bottom: 14px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    padding-bottom: 8px;
  }
`

export const SCProductFilterImg = styled.img`
  width: 34px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    width: 22px;
  }
`

export const SCProductBoxSelect = styled.div`
  display: flex;
  flex-wrap: wrap;
  justify-content: start;
`

export const SCProductFilterFlex = styled.div`
  flex: 0 0 33.33%;
  max-width: 33.33%;
  position: relative;
`

export const SCIconLocation = styled.img<{ top: any }>`
  position: absolute;
  top: ${(props) => (props.top ? props.top : '16')}px;
  max-width: 16px;
  left: 9px;
  z-index: 2;
`

export const SCIconDown = styled.img`
  position: absolute;
  z-index: 2;
  right: 13px;
  top: 19.4px;
`
