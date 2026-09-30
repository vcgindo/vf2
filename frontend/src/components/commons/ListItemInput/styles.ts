import styled from 'styled-components'

export const SCMenu = styled.div`
  position: fixed;
  box-shadow: inset 0 1px 0 rgba(0, 0, 0, 0.1);
  font-size: 14px;
  background-color: #ffffff;
  z-index: 2;
`

export const SCMenuList = styled.div`
  max-height: 300px;
  overflow-y: auto;
  position: relative;
  -webkit-overflow-scrolling: touch;
  padding-bottom: 4px;
  padding-top: 4px;
  box-sizing: border-box;
`

export const SCMenuItem = styled.div`
  cursor: pointer;
  display: block;
  font-size: inherit;
  width: 100%;
  user-select: none;
  -webkit-tap-highlight-color: rgba(0, 0, 0, 0);
  background-color: transparent;
  color: inherit;
  padding: 8px 12px;
  box-sizing: border-box;
  &:hover {
    background-color: #f2f2f2;
  }
`
