import styled from 'styled-components'
import * as globalStyles from '../../../styles/global'
import * as GridSystem from '../../../styles/gridSystem'

export const SCBoxFilterSticky = styled.div`
  position: sticky;
  top: 106px;
  z-index: 2;
  background-color: #f9f9f9;
  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    top: 113px;
  }
`

export const SCBoxFilter = styled.div`
  display: flex;
  column-gap: 20px;
  background-color: ${globalStyles.white};
  box-shadow: 0px 10px 20px #c4c8d066;
  border-radius: 12px;
  padding: 20px;
  width: 100%;
  margin-bottom: 20px;
`

export const SCSearchText = styled.div`
  position: relative;
  width: 155px;
  input {
    width: 100%;
    height: 46px;
    padding: 15px;
    box-sizing: border-box;
    padding-left: 30px;
    border-radius: 6px;
    border: 1px solid #929292;
    color: #929292;
    font-size: 1.2rem;
    outline: none;
    @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
        .size.laptopL}) {
      font-size: 9.8px;
      height: 36px;
      padding: 10px 4px 10px 28px;
    }
  }
  input[type="date"]::-webkit-calendar-picker-indicator {
    color: #d8d8d8;
    opacity: 1;
    display: block;
    /* background: url(https://mywildalberta.ca/images/GFX-MWA-Parks-Reservations.png) no-repeat; */
    width: 16px;
    height: 16px;
    border-width: thin;
    position: absolute;
    left: 4px;
  }
  img {
    position: absolute;
    left: 0px;
    top: 5px;
    padding: 10px;
    color: #f9f9f9;
    width: 35px;
    height: 35px;
    @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
        .size.laptopL}) {
      top: 0px;
    }
  }
  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    max-width: 120px;
  }
`

export const SCResetFilterBtn = styled.button<{themeUi: string}>`
  color: ${props => globalStyles.chooseThemeColor[props.themeUi]?.color5};
  background-color: #fefefe;
  padding: 8px 0px;
  border-radius: 8px;
  font-weight: 500;
  width: 164px;
  flex: 0 0 50%;
  height: 40px;
  border: 1px solid ${props => globalStyles.chooseThemeColor[props.themeUi]?.color5};
  @media only screen and (max-width: 1490px) {
    width: 100px;
  }
`

export const SCFilterBtn = styled.button<{themeUi: string}>`
  color: #ffffff;
  background-color: ${props => globalStyles.chooseThemeColor[props.themeUi]?.color5};
  padding: 8px 0px;
  font-size: 1.6rem;
  border-radius: 8px;
  width: 164px;
  height: 40px;
  border: 1px solid ${props => globalStyles.chooseThemeColor[props.themeUi]?.color5};
  flex: 0 0 50%;
  /* font-weight: 500; */
  @media only screen and (max-width: 1490px) {
    width: 100px;
  }
`

export const SCButtonFilter = styled.div`
  padding-top: 51px;
  display: flex;
  justify-content: center;
  flex: 1 0 25%;
  gap: 15px;
  text-align: center;

  @media (min-width: ${GridSystem.size.laptopL}) and (max-width: ${GridSystem
      .size.desktop}) {
    padding-top: 52px;
  }

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    padding-top: 33px;
    flex: 1 0 0%;
  }
`

export const SCQuickFilters = styled.div`
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: nowrap;
  padding-bottom: 20px;
`

export const SCTabArea = styled.div`
  display: flow-root;
  position: relative;
  margin-left: 35px;
`

export const SCBoxFilterButtonLabel = styled.p`
  font-size: 1.5rem;
  color: #000;
  margin-bottom: 12px;
  margin-left: 10px;
  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.desktop}) {
    margin-left: 4px;
  }
`

export const SCBoxFilterButtonFlex = styled.div`
  display: flex;
  align-items: center;
`

export const SCTabHeader = styled.div`
  display: flex;
  align-items: center;
  place-content: space-between;
`

export const SCTabHeaderLeft = styled.div`
  display: flex;
  position: relative;
  z-index: 1;
`

export const SCTabHeaderRight = styled.div`
  display: flex;
  align-items: center;

  .view-mode {
    width: 2.6rem;
    margin-left: 1rem;
    cursor: pointer;
  }
`

export const SCTabView = styled.p`
  font-size: 1.8rem;
  color: #292c2e;
  margin-left: 10px;
`

export const SCExportAllBoxButton = styled.button`
  background-color: ${globalStyles.white};
  border: 1px solid #11b221;
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  align-items: center;

  img {
    width: 1.3vw;
  }
`

export const SCExportAllBoxSpan = styled.span`
  color: #11b221;
  font-size: 1.3rem;
  font-weight: 500;
  padding: 0 10px;
  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    font-size: 0.9rem;
  }
`

export const SCIconLocation = styled.img`
  position: relative;
  top: 35px;
  max-width: 16px;
  left: 8px;
  z-index: 2;
`

export const SCTabButton = styled.div<{
  active: true | false
  zIndex: number
  marLeft: true | false
  themeUi: string
}>`
  color: ${(props) => (props.active ? '#FFFFFF' : '')};
  opacity: 1;
  height: 60px;
  width: 23rem;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
  position: relative;
  z-index: ${(props) => props.zIndex};
  margin-left: ${(props) => (props.marLeft ? '-1.5em' : '0')};
  padding-left: ${(props) => (props.marLeft ? '1.5em' : '0')};
  cursor: pointer;

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    font-size: 1.2rem;
    height: 3.5vw;
    width: 17rem;
  }

  ::before {
    border: 0.5px solid #cccccc;
    content: "";
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: -1;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    background: ${(props) => (props.active ? globalStyles.chooseThemeColor[props.themeUi]?.color5 : '#FCFCFC')} 0% 0%
      no-repeat padding-box;
    box-shadow: 0px 5px 25px #9d9d9d29;
    transform: scale(1.2, 1.3) perspective(0.5em) rotateX(2.5deg);
    transform-origin: bottom left;
  }
`

export const SCTabBody = styled.div`
  display: block;
  background: #ffffff 0% 0% no-repeat padding-box;
  border: 0.5px solid #cccccc;
  border-radius: 0px 15px 15px 15px;
`

export const CurrentAvailability = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 2rem 0;

  span {
    font-size: 2rem;
    font-weight: 500;
    border: 0.5px dashed rgba(18, 20, 24, 0.5);
    padding: 10px;
    border-radius: 3px;

    @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
        .size.laptopL}) {
      font-size: 1.2rem;
    }
  }
`
