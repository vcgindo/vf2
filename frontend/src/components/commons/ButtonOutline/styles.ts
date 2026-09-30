import styled from 'styled-components'
import * as gridSystem from '../../../styles/gridSystem'

export const SCButtonOutline = styled.button<{ icons: true | false }>`
  border: 1px solid #929292;
  border-radius: 6px;
  font-size: 1.2rem;
  line-height: 1.6rem;
  height: 46px;
  padding: 0 6px;
  /* margin: 0 10px; */
  margin-right: 10px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: center;
  max-height: 46px;
  background-color: ${(props) => (props.icons ? '#F9F9F9' : '#fff')};
  color: ${(props) => (props.icons ? '#929292' : '#000000')};
  border: ${(props) => (props.icons ? '1px solid #929292' : 'unset')};
  width: ${(props) => (props.icons ? '90px' : 'unset')};
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.laptopL}) {
    height: 36px;
    width: ${(props) => (props.icons ? '70px' : 'unset')};
    margin: 0 4px;
    font-size: ${(props) => (props.icons ? '11px' : 'unset')};
  }
`

export const SCButtonOutlineNoIcon = styled.button<{ status: true | false }>`
  border: 1px solid #929292;
  border-radius: 6px;
  font-size: 1.2rem;
  line-height: 1.6rem;
  height: 46px;
  width: 90px;
  padding: 0px 6px;
  margin: 0 10px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: center;
  max-height: 46px;
  background-color: ${(props) => (props.status ? '#000000' : '#F9F9F9')};
  color: ${(props) => (props.status ? '#fff' : '#929292')};
  border: ${(props) => (!props.status ? '1px solid #929292' : 'unset')};
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.laptopL}) {
    height: 36px;
    margin: 0 4px;
  }
  @media only screen and (max-width: 1490px) {
    padding: 0px 4px;
    width: 70px;
  }
`

export const SCImgOutline = styled.img`
  padding-right: 10px;
`
