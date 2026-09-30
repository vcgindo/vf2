import styled from 'styled-components'
import * as gridSystem from '../../../styles/gridSystem'

export const SCSearchText = styled.div`
  position: relative;
  width: 155px;
  input {
    width: 100%;
    padding: 15px;
    box-sizing: border-box;
    padding-left: 30px;
    border-radius: 6px;
    border: 1px solid #929292;
    color: #929292;
    font-size: 1.2rem;
    outline: none;
    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
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
    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.laptopL}) {
      top: 0px;
    }
  }
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.laptopL}) {
    max-width: 120px;
  }
`

export const SCIconLocation = styled.img`
  position: absolute;
  max-width: 16px;
  margin: 0 0 16px 8px;
  z-index: 2;
  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.laptopL}) {
    margin: 0 0 9px 8px;
  }
`
