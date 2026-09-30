import styled from "styled-components";
import * as gridSystem from "../../../../../styles/gridSystem";

export const EnquiryWrapper = styled.div`
  @media only screen and (min-width: ${gridSystem.size
    .mobileS}) and (max-width: ${gridSystem.size.mobileL}) {
    margin-left: -40px;
    margin-top: -40px;
    padding: 20px;
  }
`;

// export const FilterWrapper = styled.div`
//   padding: 0px 20px 15px;
// `;

export const EditFilterBtn = styled.button`
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  box-shadow: rgba(139, 139, 139, 0.255) -3px 3px 12px;
  background-image: linear-gradient(to right, #8d2e61, #bb3f81, #db6ba7);
`;

export const CardBtn = styled.div`
  padding: 12px;
  cursor: pointer;
  box-shadow: rgba(139, 139, 139, 0.255) -3px 3px 12px;
`;

export const RmUICont = styled.div`
  display: flex;
  flex-direction: column;
  margin-top: 20px;
  width: 50%;
  min-width: 300px;
  border-radius: 4px;
  box-shadow: rgba(139, 139, 139, 0.255) -3px 3px 12px;

  @media only screen and (min-width: ${gridSystem.size
    .mobileS}) and (max-width: ${gridSystem.size.mobileL}) {
    display: flex;
    flex-direction: row;
    margin-top: 20px;
    min-width: 300px;
    border-radius: 4px;
    box-shadow: rgba(139, 139, 139, 0.255) -3px 3px 12px;
    background-color: #f2f2f2;
  }
`;

export const HeaderWrapper = styled.div`
  display: flex;
  justify-content: space-between;
  padding: 10px 20px;
  background: white;
  gap: 1rem;
  @media only screen and (min-width: ${gridSystem.size
    .mobileS}) and (max-width: ${gridSystem.size.mobileL}) {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 10px 20px;
    align-items: center;
    background-color: white;
  }
`;

export const RmHeading = styled.div`
  color: #000000;
  font-family: "Roboto";
  font-size: 12px;
`;

export const VerticalLine = styled.div`
  width: 1px;
  background-color: #d4d4d4;
`;

export const ValueWrapper = styled.div`
  display: flex;
  justify-content: space-between;
  padding: 10px 40px;
  background-color: #f2f2f2;
  border-radius: 0px 0px 4px 4px;
  font-size: 12px;
  @media only screen and (min-width: ${gridSystem.size
    .mobileS}) and (max-width: ${gridSystem.size.mobileL}) {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 10px 40px;
    border-radius: 0px 0px 4px 4px;
  }
`;

export const HighlightedValue = styled.div`
  color: #bb3f81;
  font-weight: 500;
`;

export const EstimatedWrapper = styled.div`
  position: relative;
  margin: 1rem 0;
  overflow-y: scroll;
`;
export const BlurCover = styled.div`
  top: 0;
  // left: 1%;
  position: absolute;
  background: #80808080;
  width: 98%;
  height: 100%;
  border-radius: 20px;
`;

export const CardCover = styled.div`
  height: 100%;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
`;
export const DashedCard = styled.div`
  padding: 50px 40px;

  border: 1px dashed #bb3f81;
  border-radius: 10px;
  background: white;
  opacity: 1;
  display: flex;
  justify-content: center;
  align-items: center;
`;
export const MessageText = styled.span`
  font-family: "Roboto", sans-serif;
  font-weight: 300;
  font-size: 16px;
  color: #000000;
  letter-spacing: 0;
  line-height: 30px;
`;

export const TabSwitchContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 50px;

  @media (min-width: ${gridSystem.size.mobileS}) and (max-width: ${gridSystem
    .size.mobileL}) {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    width: 100%;
  }
`;

export const TabSwitchHeading = styled.div`
  font-family: "Roboto";
  font-weight: 500;
  font-size: 14px;
  color: #000000;
  letter-spacing: 0;
  line-height: 24px;
`;

export const TabsWrapper = styled.div`
  width: 18%;
`;

export const BTRLayoutWrapper = styled.div`
    display:flex;
    flex-direction:column;
    height:90%;
`

export const BTRLayoutTabsWrapper = styled.div`
    display:flex;
    justify-content:center;
    margin-top:25px;
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
    margin-top:20px;
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
    margin:0px 25px;
`

export const BTRAvailabiltyCellRendererWrapper = styled.div`
    height:100%;
    width:100%;
    display:flex;
    align-items:center;
    justify-content:center;
`

export const BTRAvailabiltyCellRenderer = styled.div<{ value: number,themeUi:string  }>`
    position:relative;
    height:100%;
    max-height:15px;
    width:45px;
    background: #DEDEDE 0% 0% no-repeat padding-box;
    &::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        bottom:0;
        width:${(props) => props.value}%;
        // background: transparent linear-gradient(270deg, #EB73B3 0%, #820F4C 100%) 0% 0% no-repeat padding-box;
        background: ${(props) =>props.themeUi === "REGALBLAZE"? "linear-gradient(90deg, #FCA311 0%, #CB830E 100%) 0% 0% no-repeat padding-box": "linear-gradient(90deg, #EB73B3 0%, #820F4C 100%) 0% 0% no-repeat padding-box"};

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

export const LockBtn = styled.img`
    position:absolute;
    height:25px;
    width:25px;
    cursor:pointer;
`

export const HorizontalViewWrapper = styled.div`
      display:flex;
      width:100%;
`


export const Separator = styled.div`
      height: 100%;
      width: 15px;
      margin: 5px;
      display: flex;
      justify-content: center;
      align-items: center;
      pointer-events: none;
`