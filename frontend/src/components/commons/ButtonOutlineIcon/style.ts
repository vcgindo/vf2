import styled from 'styled-components'
import * as globalStyles from '../../../styles/global'

export const SCButtonOutlineIcon = styled.button<{themeUi: string,disabled:boolean}>`
  width: 100%;
  height: 100%;
  color: ${props => globalStyles.chooseThemeColor[props.themeUi]?.color5};
  font-size: 16px;
  border-radius: 6px;
  font-weight: 500;
  opacity: 1;
  border: 1px solid ${props => globalStyles.chooseThemeColor[props.themeUi]?.color5};
  background-color: ${globalStyles.white};
  cursor:${props => props.disabled ? 'not-allowed':'pointer'};
`

export const SCImg = styled.img`
  padding-right: 10px;
`
