import styled from 'styled-components'

export const VFSelectedFiltersWrapper = styled.div`
   // max-width:800px;
   overflow:auto;
   width:100%
    height: 51px;
    padding:5px;
    display:flex;
    align-items:center;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: 0px 6px 12px #95959529;
    border-radius: 30px;
    margin-left: auto;
    // overflow-x:overlay;
//     ::-webkit-scrollbar {
//      width: 0.2px;
//      display:none;
//    }
`


export const VFSelectedFiltersPlaceHolder = styled.p`
    height: 39px;
    border-radius: 20px;
    font-weight:400;
    display:flex;
    align-items:center;
    font-size:16px;
    line-height:21px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #313131;
    padding:5px 15px;
    text-wrap:nowrap;
    white-space:nowrap;
   // margin-right:-15px;
//    min-width:140px;
`

export const VFSelectedFiltersChip = styled.span`
    height: 39px;
    display:flex;
    align-items:center;
    padding:5px;
    padding-left:10px;
    background: #F2F2F2 0% 0% no-repeat padding-box;
    border-radius: 20px;
    margin-left:10px;

    
`

export const VFSelectedFiltersFilterLabel = styled.div`
font-size:16px;
line-height:21px;
font-family:Roboto;
font-weight:300;
letter-spacing: 0px;
color: #313131;
`

export const VFSelectedFiltersFilterContent = styled.div`
    display:flex;
    flex-direction:row;
    padding:0 10px;
    border-right:solid 2px black;
`

export const VFSelectedFiltersFilterValue = styled.p`
font-size:16px;
line-height:21px;
font-family:Roboto;
letter-spacing: 0px;
display:flex;
text-wrap:nowrap;

`

export const VFSelectedFiltersFilterCloseIcon = styled.img`
    margin-left:5px;
    height:18px;
    width:18px;
    border-radius:50%;
    border:solid 1px black;
    cursor:pointer;
`
export const VFFilterScrollBar = styled.div`
overflow-x:overlay;
display:flex;

::-webkit-scrollbar {
    width: 0.2px;
    display:none;
  }
`