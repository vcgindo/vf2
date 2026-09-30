import styled from 'styled-components';


export const ApplyZoomOut = styled.div`
    zoom: 0.7;
`

export const OrderReschedulingWrapper = styled.div`
  & .toolbar-container{
    margin: 0;
    padding-top: 20px;
  }
`

export const VFTableWrapper = styled.div<{ height?: string, disableZoomScaling?: boolean }>`
    // height: 75vh;
    height: 100%;
    // margin-top: 20px;
    padding-left: 20px;
    display: flex;
    flex-direction: column;

    & div[data-testid="vf_pagination"]{
      margin-top: 0 !important;
    }


 
    // & .ag-theme-alpine {
    //   flex: 1;
    //     margin: 0 !important;
    //   }
    & .ag-theme-noir-fusion {
        margin: 0 !important;
      }
    
`
export const PaginationWrapper = styled.div`

`


export const ETACellRendererWrapper = styled.div`
    display:flex;
    justify-content:center;
    align-items:center;
    height:100%;
    width:100%;
    padding: 1rem;
`

export const ETACellValue = styled.p`
    display:flex;
    justify-content:center;
    align-items:center;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: 0px 6px 12px #77777729;
    border: 0.4000000059604645px solid #707070;
    border-radius: 2px;
    height:30px;
    width:100%;
    padding:4px;
`

export const DatePickerWrapper = styled.div`
    display: flex;
    cursor: pointer;
    flex-direction: row;
    width: 180px;
    padding: 5px;
    justify-content: sapce-between;
`;

export const TextInputWrapper = styled.input<{theme: string}>`
    width: 80%;
    height: 100%;
    text-align: center;
    letter-spacing: 0px;
    opacity: 1;
    font-size: 12px;
    padding: 4px;
    font-weight: 400;
    font-family: Roboto;
    border: none;
    pointer-events: none;
`;

export const DateInputWrapper = styled.input`
    opacity: 0;
    position: absolute;
    pointer-events: none;
`;

export const ButtonWrapper = styled.button`
    background: none;
`;

export const ImageWrapper = styled.img`
    cursor: pointer;
    height: 15px;
    width: 15px;
`;

