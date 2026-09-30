import styled from 'styled-components'
import * as gridSystem from '../../../styles/gridSystem'

export const SCSelectOption = styled.div`
  position: relative;
`

export const SCSelectIcon = styled.img`
  position: absolute;
  top: 50%;
  color: #333;
  transform: translateY(-50%);
  pointer-events: none;
  left: 8px;
`

export const SCSelectBox = styled.select<{
  icons: true | false
  icon: true | false
  name: string
}>`
  padding-left: ${(props) =>
    props.icons ? '28px' : props.icon ? '4px' : '24px'};
  border: ${(props) =>
    props.icon ? '1px solid #929292' : '1px solid #D8D8D8'};
  color: ${(props) => (props.icon ? '#929292' : '')};
  background-color: ${(props) => (props.icon ? '#F9F9F9' : '')};
  padding-right: 3px;
  border-radius: 6px;
  height: 46px;
  width: 100%;
  /* width: ${(props) => (props.name === 'style' ? '73px' : '100%')}; */

  font-size: 12px;
  font-family: "Roboto";
  line-height: 1.8rem;
  &:focus-visible {
    outline: none;
  }
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.laptopL}) {
    height: 36px;
  }
  /* @media only screen and (min-width: 1200px) {
    width: ${(props) => (props.name === 'locationFilter' ? '96px' : '84px')}
  } */
`
