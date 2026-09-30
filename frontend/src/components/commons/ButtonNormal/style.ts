import styled from 'styled-components'
import * as globalStyles from '../../../styles/global'
import * as gridSystem from '../../../styles/gridSystem'

export const SCButtonNormal = styled.button<{ isHide: boolean }>`
  border: none;
  color: ${globalStyles.white};
  background-color: ${globalStyles.mainColor};
  padding: 8px 24px;
  font-size: 1.6rem;
  border-radius: 8px;
  font-weight: 500;
  white-space: break-spaces;
  max-width: 140px;
  ${(props) => (props.isHide ? 'display: none' : '')};
  @media (min-width: ${gridSystem.size.laptop}) {
    font-size: 1rem;
    padding: 4px 6px;
  }
`
