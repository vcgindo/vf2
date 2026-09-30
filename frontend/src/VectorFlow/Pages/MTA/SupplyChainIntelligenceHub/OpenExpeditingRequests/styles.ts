import styled from 'styled-components'


export const ETACellRendererWrapper = styled.div`
    display:flex;
    justify-content:center;
    align-items:center;
    height:100%;
    width:100%;

`

export const ETACellValue = styled.p`
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: 0px 6px 12px #77777729;
    border: 0.4000000059604645px solid #707070;
    border-radius: 2px;
    height:100%;
    width:100%;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
`

export const SubmitRemarkInputWrapper = styled.div`
    height:90%;
    width:100%;
    border:solid 1px black;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
`

export const ButtonWrapper = styled.div`
    width:100%;
    display:flex;
    justify-content:flex-end;
    padding-right:20px;
    zoom:0.7;
`

export const DatePickerWrapper = styled.div`
    display: flex;
    cursor: pointer;
    flex-direction: row;
    width: 180px;
    padding: 5px;
    justify-content: sapce-between;
`;

export const TextInputWrapper = styled.input`
  width: 80%;
  height: 100%;
  text-align: center;
  font: 12px;
  letter-spacing: 0px;
  opacity: 1;
  font-size: 12px;
  padding: 4px;
  font-style:normal;
  font-variant:normal;
  font-weight: medium;
  font-family: Roboto;
  border: none;
  pointer-events: none;
  background: transparent;
`;

export const DateInputWrapper = styled.input`
  opacity: 0;
  position: absolute;
  pointer-events: none;
`;

export const ButtonWrapperForSubmitRemark = styled.button`
  margin-right: 30px;
  background: none;
`;

export const ImageWrapper = styled.img`
  cursor: pointer;
  height: 20px;
  width: 20px;
`;