import styled from "styled-components";
import { storeCellColors } from "../../../../../../helpers/utils";

import * as globalStyles from '../../../../../../styles/global'

export const ViewWrapper = styled.div`
  height: 100%;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding-left: 20px;
  padding-top:20px;
  padding-bottom:20px;
`;

export const ViewContainer = styled.div`
  width: 100%;
  height: 100%;
  box-shadow: rgba(99, 99, 99, 0.2) 0px 2px 8px 0px;
  border-radius: 6px;
  background-color: white;
  padding:0px 20px 0px 10px;
  display: grid;
  grid-gap:0px 5px;
  grid-template-columns: 1fr 5fr;
  grid-template-rows: auto 1fr auto; /* Adjusted for top bar, grid, and bottom bar */
`;

export const ViewSidebar = styled.div`
  grid-row: 2 / 3; /* Span all three rows */
  grid-column: 2 / 1;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  display: grid;
  grid-template-rows: repeat(4, 1fr);
`;

export const ViewTopbar = styled.div`
  grid-row: 1 / 2; /* Top bar on the first row */
  grid-column: 2 / 3;
  height: 90px;
  display: flex;
  align-items: center;
  justify-content: center;
`;

export const ViewBottombar = styled.div`
  grid-row: 4 / 4; /* Bottom bar on the last row */
  grid-column: 2 / 3;
  height: 90px;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
`;

export const ViewGridWrapper = styled.div`
  grid-row: 2 / 3; /* Positioned between top and bottom bar */
  grid-column: 2 / 3;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(4, 1fr);
  // gap:1px;
  background-color:#707070;
  border: 0.5px solid #707070;
  border-right:none;
`;

export const ViewGridCell = styled.div<{status:string}>`
  position:relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color:${(props)=>storeCellColors[props.status].backgroundColor};
  border:solid 1px ${(props)=>storeCellColors[props.status].border};
  border-right:solid 1px #929491ff;
  border-left:none;
`;

export const ViewTableLabelCellWrapper= styled.div`
    height:100%;
    width:100%;
    display:flex;
    align-items:center;
    justify-content:center;
`

export const ViewTableLabelCell = styled.div`
    width: 150px;
    height: 55px;
    box-shadow: inset -5px 5px 20px #00000029;
    border-radius: 6px;
    display:grid;
    place-items:center;
    font-family:Roboto;
    font-size:16px;
    font-weight:600;
`

export const FloatingIconWrapper = styled.div`
    position:relative;
    padding:3px 10px;
    border:solid 1.5px #696969;
    border-radius:4px;
    background-color:white;
`

export const FloatingIconPostfix = styled.img`
    position:absolute;
    width:20px;
    right:-13px;
    top:25px;
`

export const CellIconWrapper = styled.div`
    display:flex;
    flex-direction:column;
    align-items:center;
    width:75px;
`

export const CellIconLabel = styled.span`
    font-family:Roboto;
    font-size:10px;
    font-weight:400;
    line-height:15px;
`

export const CellIcon = styled.div`
    height:40px;
    width:40px;
`

export const ToolTipWrapper = styled.div`
    position:fixed;
    color:white;
    background-color:rgb(0,0,0,0.9);
    box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
    border-radius:8px;
    font-weight:500;
    font-size:10px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #FFFFFF;
    /*  */
    padding:5px;
    z-index:10000;
    &::after {
        content: '';
        position: absolute;
        bottom: 0%;
        left: 50%;
        transform: translate(-50%, 100%);
        border-width: 6px;
        border-style: solid;
        border-color: black transparent transparent transparent; /* Updated to black */
    }
`

export const ContributionWrapper = styled.div<{themeUI:string}>`
  position:absolute;
  display:flex;
  top:10px;
  left:10px;
  background: #FFFFFF 0% 0% no-repeat padding-box;
  box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
  cursor:default;
  color:${(props)=>globalStyles.chooseThemeColor[props.themeUI].color5};
  overflow:hidden;
  height:15px;
`

export const ContributionSection = styled.p`
  font-weight:500 ;
  font-size: 10px;
  font-family: Roboto;
  color:inherit;
  padding:0px 3px;
`

export const ContributionHiddenSection = styled.div<{isOpen:boolean}>`
  display:flex;
  height:100%;
  align-items:center;
  width:${(props)=>props.isOpen?'auto':0};
  font-weight:500 ;
  font-size: 10px;
  font-family: Roboto;
  color:inherit;
  transition: 0.3s ease-in-out;
  padding-right:3px;
`

export const ContributionIcon = styled.img`
  margin:0px 3px;
  height:10px;
  width:10px;
`
export const InventoryToolTipContent = styled.div`
  padding:0px 5px;
`

export const DetailToolTipWrapper = styled.div`
  display:flex;
  flex-direction:column;
  padding:2px;
  color:white;
  width:200px;
`

export const DetailToolTipHeader = styled.div`
  border-bottom:dashed 1px white;
`

export const DetailToolTipGrid = styled.div`
 display:flex;
 flex-direction:column;
`

export const DetailToolTipGridRow = styled.div`
 display:grid;
  grid-template-columns:2fr 1fr 1fr;
  padding:3px 5px;
`
export const HighlightedRow = styled(DetailToolTipGridRow)`
  background-color:#404040ff;
`

export const DetailToolTipGridHeader =  styled.span`
  display:flex;
  justify-content:center;
  width:100%;
  font-weight:500;
  font-size:10px;
  color:white;
`

export const DetailToolTipGridCell =  styled.span`
  width:100%;
  font-size:10px;
  display:flex;
  justify-content:center;
`