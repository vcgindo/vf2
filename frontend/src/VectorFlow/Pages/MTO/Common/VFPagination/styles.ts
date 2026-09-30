import styled from "styled-components";

export const PaginationWrapper = styled.div`
    display:flex;
    flex-direction:column;
    
    border-radius:inherit;
    margin-top:0px;
    position:relative;
    // z-index:20;
`

export const SelectedRowsCountWrapper = styled.div`
    width:100%;
    margin-bottom:10px;
    font-style:normal;
    font-variant:normal;
    font-weight:300;
    font-size:14px;
    font-family:Roboto;
    line-height:20px;
    color: #313131;
    padding-left:32px;
    opacity:1;
`

export const TotalItemsWrapper = styled.div`
    display:flex;
    align-items:center;
    // border: 0.800000011920929px solid #C7C7C7;
    // border-left:none;
    // border-right:none;
    
`

export const StatusBarLabelsWrapper = styled.div`
    width:100%;
    display:flex;
    flex-direction:row;
    height:40px;
    padding:0 10px;
    font-size:13px;
    font-family:Roboto;
    line-height:19px;
    letter-spacing: 0px;
    color: black;
    border:1px solid #babfc7;
    border-top:none;
`

export const PaginationContainer = styled.div`
    width:100%;
    display:flex;
    flex-direction:row;
    height:40px;
    padding:0 10px;
    font-size:13px;
    font-family:Roboto;
    line-height:19px;
    letter-spacing: 0px;
    color: black;
    justify-content:space-between;
    // border:1px solid #babfc7;
    box-shadow:0px 6px 12px #95959529;
    border-top:none;
    background-color:white;
    // margin-top:-20px;
     alignItems: 'center'
`
export const CustomPageSize = styled.div`
    display:flex;
    flex-direction:row;
    font-variant:normal;
    align-items:center;
    font-size:11px;
    font-family:Roboto;
    line-height:19px;
    letter-spacing: 0px;
    color: black;
    height: 70%;
    width: 140px
`

export const StatusBarLabel = styled.div`
    display:flex;
    flex-direction:row;
    font-variant:normal;
    align-items:center;
    font-size:13px;
    font-family:Roboto;
    line-height:19px;
    letter-spacing: 0px;
    color: black;
`
export const StatusBarLabelLight = styled.div`
    font-weight:400;
    margin-left:5px;
`

export const StatusBarLabelBold = styled.div`
    font-weight:700;
    margin-left:5px;
`

export const PaginationHandlersWrapper = styled.div`
display:flex;
flex-direction:row;
align-items:center;
`

export const PaginationArrowIcon = styled.img<{ disabled: boolean }>`
    margin-left:5px;
    cursor:pointer;
    height:10px;
    width:10px;
    opacity:${(props) => props.disabled ? 0.3 : 1};
`
export const StatusBarWrapper = styled.div`
    display:flex;
    flex-direction:row;
    align-items:center;
`
export const GridFilterWrapper = styled.div`
    zoom:0.5;
    display:flex;
    align-items:center;
    justify-content:center;
`

export const TextBtn= styled.button<{themeUi: string}>`

    font-family: 'Roboto';
    font-weight: 500;
    font-size: 23px;
    line-height: 24px;
    display: flex;
    align-items: center;
    cursor:pointer;
    background-color:white;
    color:${(props)=>props.themeUi ==='REGALBLAZE'? '#CB830E' :'#BC3D81'};

     &:disabled{
        color:grey;
        cursor:context-menu;
    }
`

export const PageSizeInputDiv= styled.div`
    border-radius: 5px;
    background: white;
    display: flex;
    justify-content: center;
    align-items: center;
    box-shadow: rgba(133, 132, 132, 0.247) 5px 0px 10px;
    height: 100%;
    width: 80px;
    margin-left: 5px;
`
export const PageSizeInput= styled.input<{themeUi: string}>`
    font-family: 'Roboto';
    font-size: 11px;
    line-height: 19px;
    display: flex;
    align-items: center;
    cursor:pointer;
    background-color:white;
    letter-spacing: 0px;
    color: black;
    width: 70%;
    height: 100%;
    border: 1px solid white;
    padding: 2px 5px;
    outline: none;
    &:hover {
        border: 1px solid ${(props)=>props.themeUi ==='REGALBLAZE'? '#CB830E' :'#BC3D81'}; /* Adjust the color to your preference */
    }

    &:focus {
        border: 1px solid ${(props)=>props.themeUi ==='REGALBLAZE'? '#CB830E' :'#BC3D81'}; /* Adjust the color to your preference */
    }
`