import styled from 'styled-components'
import * as gridSystem from '../../../styles/gridSystem'

export const SCLocationFilter = styled.div`
  width: 90%;
  padding-right: 20px;
  border-right: 1px solid #d8d8d8;
  @media only screen and (max-width: 1280px) {
    width: 100%;
  }
`

export const SCProductFilterImg = styled.img`
  width: 34px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.laptopL}) {
    width: 22px;
  }
`

export const SCProducFilterHeader = styled.div`
  display: flex;
  align-items: center;
  padding-bottom: 14px;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.laptopL}) {
    padding-bottom: 8px;
  }
`

export const SCProductBoxSelect = styled.div`
  display: flex;
  flex-wrap: wrap;
  /* justify-content: space-between; */
`

export const SCProductBoxSelectItem = styled.div<{ width: number }>`
  flex: 1 0 ${(props) => props.width}%;
  max-width: ${(props) => props.width}%;
  position: relative;
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

export const SCIconLocation = styled.img<{ locationIcon: boolean }>`
  position: absolute;
  top: ${(props) => (props.locationIcon ? '16' : '19')}px;
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
