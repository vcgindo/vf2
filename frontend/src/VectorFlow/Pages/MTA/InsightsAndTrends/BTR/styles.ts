import styled from "styled-components";


export const BTRLayoutWrapper = styled.div`
    display:flex;
    flex-direction:column;
    height:85%;
    margin-left:5px;
`

export const BTRLayoutTabsWrapper = styled.div`
    display:flex;
    justify-content:center;
    margin-top:5px;
    z-index:200;
`

export const ToggleViewBtnWrapper = styled.div`
    position:absolute;
    right:35px;
    zoom:0.6;
    z-index:0;
    margin-top:-10px;
`

export const BTRTableWrapper = styled.div`
    display:flex;
    flex-direction:column;
    height:400px;
    width:100%;
    margin-top:10px;
    margin-bottom:20px;
    height:100%;
`

export const BTRAllomentSection = styled.div`
    display:flex;
    flex-direction:column;
    height:100%;
    max-height:100%;
`

export const BTRTableHeader = styled.p`
    font-size:13px;
    font-weight:500;
    margin:15px 25px 0px;
    height:35px;
`

export const BTRAvailabiltyCellRendererWrapper = styled.div`
    height:100%;
    /* width:150px; */
    display:flex;
    align-items:center;
    justify-content:center;
`

export const BTRAvailabiltyCellRenderer = styled.div<{ value: number , themeUi:string }>`
    position:relative;
    height:100%;
    max-height:15px;
    width:45px;
    max-width: 45px;
    background: #DEDEDE 0% 0% no-repeat padding-box;
    &::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        bottom:0;
        max-width: 45px;
        width:${(props) => props.value}%;
        // background: transparent linear-gradient(270deg, #EB73B3 0%, #820F4C 100%) 0% 0% no-repeat padding-box;
         background:  ${(props)=>props.themeUi==="REGALBLAZE"?"transparent linear-gradient(270deg, #FCA311  0%, #CB830E 100%) 0% 0% no-repeat padding-box" :"transparent linear-gradient(270deg, #EB73B3 0%, #820F4C 100%) 0% 0% no-repeat padding-box"};
     
        }
`


export const CategoryCellRendererWrapper = styled.div`
height: 100 %;
width: 100 %;
display: flex;
align - items: center;
justify - content: center;
`

export const CategoryCellRendererChip = styled.div`
    width: 18px;
    min-width:18px;
    height: 18px;
    display:flex;
    font-size:8px;
    font-family:Roboto;
    align-items:center;
    justify-content:center;
    margin-left:5px;
    background-color: #355FD3;
    border-radius:4px;
    box-shadow: 0px 4px 5px #00000043;
`

export const AvailabilityToolTipWrapper = styled.div`
    height: 27px;
    display:flex;
    align-items:center;
    justify-content:center;
    background-color: black;
    color:white;
    padding:15px;
    border-radius: 4px;
    font-size:9px;
`

export const CategoryToolTipWrapper = styled.div`
    display:flex;
    flex-direction:column;
    width: 150px;
    border-radius:4px;
    overflow:hidden;
`

export const CategoryToolTipSection = styled.div`
width: 100 %;
padding: 10px;
display: flex;
flex - direction: column;
`

export const CategoryToolTipSectionHeader = styled.p`
    font-weight:500;
    width:100%;
    font-size:10px;
    text-align:center;
    font-family:Roboto;
`

export const CategoryToolTipSectionDescription = styled.div`
    font-weight:300;
    font-size:9px;
    text-align:center;
    font-family:Roboto;
    margin-top:5px;
`

export const LockBtnWrapper = styled.div`
    position:relative;
    z-index:300;
`
export const LocktBtnContent = styled.div`
    display:flex;
    flex-direction:column;
   align-items:center;
    position:absolute;
    width:75px;
`

export const LockBtn = styled.img`
    height:20px;
    width:20px;
    cursor:pointer;
`

export const LockLabel = styled.div`
      font-size:12px;
`

export const HorizontalViewWrapper = styled.div`
      display:flex;
      width:100%;
`

export const VerticalViewLeftTableWrapper = styled.div`
      display:flex;
      height:95%;
      width:100%;
      padding-right:10px;
`
