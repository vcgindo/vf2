import styled from 'styled-components'
import * as globalStyles from '../../../styles/global'

export const SCIstStatusRow = styled.div`
  display: flex;
  flex-wrap: wrap;
  position: relative;
  width: 100%;
`

export const SCIstStatusTable = styled.div`
  width: 100%;
  overflow: auto;
  // max-height: 74vh;
  position: relative;
`

export const SCIstStatusText = styled.p`
  font-size: 1.2rem;
  color: #b4b4b4;
  padding-bottom: 10px;
`

export const SCIstStatusFIlterBox = styled.div`
  padding: 30px 15px;
  background-color: ${globalStyles.white};
  width: 100%;
`

export const SCIstComponent = styled.div`
  background-color: #b4b4b4;
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
  color: ${globalStyles.white};
  font-size: 2rem;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 10px 0;
`

export const SCIstStatusSettingPanel = styled.div`
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
`

export const SCIstStatusAddButton = styled.button`
  background-color: ${globalStyles.white};
  font-size: 1.2rem;
  font-weight: 500;
  text-decoration: underline;
`

export const SCIstStatusInput = styled.input`
  display: none;
`

export const SCIstStatusLabel = styled.label<{ active: true | false, themeUi: string }>`
  display: inline-flex;
  margin: 4px 0;
  position: relative;
  border-radius: 2px;
  font-size: 1.2rem;
  background: ${(props) => (props.active ? globalStyles.chooseThemeColor[props.themeUi]?.color5 : '#fff')};
  border: ${(props) =>
    props.active ? '1px solid '+ globalStyles.chooseThemeColor[props.themeUi]?.color5 : '1px solid #929292'};
  color: ${(props) => (props.active ? '#fff' : '#929292')};
  cursor: pointer;
  justify-content: center;
  align-items: center;
  padding: 4px 10px;
  box-sizing: border-box;
`

export const SCIstStatusAddText = styled.p`
  font-size: 1.2rem;
`

export const SCIstStatusAddNew = styled.div`
  display: flex;
  justify-content: space-between;
`
export const AlertNoRecords = styled.div`
  font-size: 1.5rem;
  background-color: ${globalStyles.mainColor};
  color: ${globalStyles.white};
  width: 100%;
  display: flex;
  align-items: center;
  padding: 1rem 1rem;
  border-radius: 0.5rem;
`