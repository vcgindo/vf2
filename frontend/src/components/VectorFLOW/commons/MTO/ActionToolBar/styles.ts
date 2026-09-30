import { ColorsMTO } from "../../../../../VectorFlow/Pages/MTO/Common/Colors";
import styled from "styled-components";
import * as globalStyles from '../../../../../styles/global'
import * as gridSystem from "../../../../../styles/gridSystem";

export const SCTaskBarContainer = styled.div`
  //margin-top:5px;
  // margin-bottom:10px;
  padding : 0 25px;
  display: flex;
  align-items: center;
  //margin-bottom:20px;
  margin-left: 20px;
  margin-top: 20px;
  width: 100%;
  justify-content: space-between; //changed

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.desktop}) {
    zoom: 0.7;
  }

  @media (min-width: ${gridSystem.size.desktop}) {
    zoom: 1;
  }
`;
export const SCGoBackContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  text-wrap: nowrap;
  width: max-content;
`;

export const SCGoBackText = styled.div`
  font-weight: 500;
  font-size: 20px;
  font-family: Roboto;
  letter-spacing: 0px;
  color: ${ColorsMTO.Black};
`;

export const SCViewContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  overflow: hidden;
  gap:2px;

   &:hover {
    transform: scale(1.05);
    transition: all 0.3s ease-in-out;
  }

`;
export const SCHorizontalDivison = styled.div`
  height: 40px;
  width: 2px;
  background: ${ColorsMTO.LightGrey.code};
  margin: 0 20px;
`;

export const SCViewContainerWithBg = styled.div<{styles?:any}>`
  display: flex;
  flex-direction: column;
  background: ${ColorsMTO.White} 0% 0% no-repeat padding-box;
  box-shadow: -5px 4px 10px #8584843f;
  border-radius: ${(props)=> props.styles?.borderRadius || "5px"};
  padding: ${(props) => props.styles?.padding || "1px"};
  padding-top:5px;
  justify-content: center;
  align-items: center;
  width:fit-content;
  height:fit-content;
  min-width:  ${(props)=> props.styles?.width || "82px"};
  min-height: ${(props) => props.styles?.height || "58px"};
  cursor: pointer;

  // font-size: ${(props) => props.styles?.fontSize || "16px"};
  
  &:hover {
    transform: scale(1.05);
    transition: all 0.3s ease-in-out;
  }
`;

export const SCViewContainerWithBgToggle = styled.div`
  display: flex;
  background: ${ColorsMTO.White} 0% 0% no-repeat padding-box;
  box-shadow: -5px 4px 10px #8584843f;
  border-radius: 5px;
  padding: 5px;
  justify-content: center;
  align-items: center;
  width:fit-content;
  height:fit-content;
  min-width: 164px;
  min-height: 58px;
  cursor: pointer;

   
`;
export const SCViewBackground = styled.div`
  display: flex;
  background: ${ColorsMTO.White} 0% 0% no-repeat padding-box;
  box-shadow: -5px 4px 10px #8584843f;
  border-radius: 5px;
  padding: 10px;
  // height:58px;
`;
export const SCVerticalDivider = styled.div`
  width: 0.5px;
  background-color: ${ColorsMTO.White};
  height: 40px;
  margin-right: 8px;
  margin-left: 8px;
  align-items: center;
`;

export const SCVerticalDividerGray = styled.div`
  width: 0.5px;
  background-color: #c7c7c7;
  height: 40px;
  margin-right: 8px;
  margin-left: 8px;
  align-items: center;
`;

export const SCViewImage = styled.img`
  width: 38px;
  height: 20px;
  margin-bottom: 7px;
  cursor: pointer;
`;

export const SCCustomActionsContainer = styled.div`
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: flex-end;
`;
export const SCTaskFilterContainer = styled.div`
  display: flex;
  justify-content: space-between;
  gap: 30px;
  max-width: 40%;
  align-items: center;
`;

export const SCPrimaryButton = styled.button`
  border-radius: 6px;
  font-size: 16px;
  font-family: "Roboto";
  letter-spacing: 0px;
  font-weight: 300;
  color: #ffffff;
  padding: 15px 7px;
  pointer-events: "all";
  width: 130px;
  height: 46px;
  box-shadow: -5px 4px 10px ${ColorsMTO.LightGrey};
  border: 1px solid ${ColorsMTO.Pink};
  opacity: 1;
  background-image: linear-gradient(
    to right,
    rgb(141, 46, 97),
    rgb(187, 63, 129),
    rgb(219, 107, 167)
  );
`;

export const SCButton = styled.button`
  background: ${ColorsMTO.White.code};
  border-radius: 6px;
  font-size: 16px;
  font-family: "Roboto";
  letter-spacing: 0px;
  font-weight: 300;
  color: ${ColorsMTO.Pink.code};
  padding: 15px 7px;
  pointer-events: "all";
  width: 130px;
  height: 46px;
  box-shadow: -5px 4px 10px ${ColorsMTO.LightGrey.code};
  border: 1px solid ${ColorsMTO.Pink.code};
  opacity: 1;

    &:hover {
    transform: scale(1.05);
    transition: all 0.3s ease-in-out;
  }
`;

export const AddFilterWrapper = styled.div`
&:hover {
    transform: scale(1.05);
    transition: all 0.3s ease-in-out;
  }
`

/**for Search filter */
export const VFSelectedFiltersWrapper = styled.div`
    overflow:auto;
    height: 51px;
    padding:5px;
    display:flex;
    align-items:center;
    background: ${ColorsMTO.White} 0% 0% no-repeat padding-box;
    box-shadow: 0px 6px 12px #95959529;
    border-radius: 30px;
    margin-right: 20px;
    margin-left:20px;
`;

export const VFSelectedFiltersPlaceHolder = styled.p`
  height: 39px;
  border-radius: 20px;
  font-weight: 400;
  display: flex;
  align-items: center;
  font-size: 16px;
  line-height: 21px;
  font-family: Roboto;
  letter-spacing: 0px;
  color: #313131;
  padding: 5px 15px;
  text-wrap: nowrap;
`;

export const VFSelectedFiltersChip = styled.span`
  height: 39px;
  display: flex;
  align-items: center;
  padding: 5px;
  padding-left: 10px;
  background: #f2f2f2 0% 0% no-repeat padding-box;
  border-radius: 20px;
  margin-left: 10px;
`;

export const VFSelectedFiltersFilterLabel = styled.div`
  font-size: 16px;
  line-height: 21px;
  font-family: Roboto;
  font-weight: 500;
  letter-spacing: 0px;
  color: #313131;
  display: flex;
  width: max-content;
`;

export const VFSelectedFilterLabel = styled.div`
  font-size: 16px;
  line-height: 21px;
  font-family: Roboto;
  font-weight: 200;
  letter-spacing: 0px;
  color: #313131;
  display: flex;
  width: max-content;
`;

export const VFSelectedFiltersFilterContent = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
`;

export const VFSelectedFiltersFilterValue = styled.div`
  font-size: 16px;
  line-height: 21px;
  font-family: Roboto;
  letter-spacing: 0px;
  display: flex;
  text-wrap: nowrap;
`;
export const SCFilterVerticalDivider = styled.div`
  width: 0.5px;
  background-color: black;
  height: 20px;
  align-items: center;
  margin: 0px 8px;
`;

export const VFSelectedFiltersFilterCloseIcon = styled.img`
  margin-left: 5px;
  height: 18px;
  width: 18px;
  border-radius: 50%;
  border: solid 1px black;
  cursor: pointer;
`;
export const VFFilterScrollBar = styled.div`
  overflow-x: overlay;
  display: flex;
  ::-webkit-scrollbar {
    width: 0.2px;
    display: none;
  }
`;

/**release date */
export const VFReleaseDateWrap = styled.div`
  display: flex;
  justifycontent: space-between;
  alignitems: center;
  marginright: 3px;
  fontsize: 18px;
  fontweight: bold;
  width: 70%;
`;
export const VFReleaseDateCompWrap = styled.div`
  top: 133px;
  left: 638px;
  width: 204px;
  height: 43px;
  background: #ffffff 0% 0% no-repeat padding-box;
  border: 0.5px solid #acacac;
  borderradius: 4px;
  opacity: 1;
`;

export const VFInputDate = styled.input`
  top: 141px;
  left: 651px;
  width: 100%;
  height: 100%;
  textalign: left;
  font: 24px;
  letterspacing: 0px;
  color: #000;
  opacity: 1;
  fontsize: 18px;
  padding: 4px;
  fontweight: bold;
  fontfamily: Roboto;
  border: 0.5px solid #acacac;
`;
/**release date */
/**constant date */

export const DateWrapper = styled.div`
  display: flex;
  align-items: center;
  gap: 15px;
  font-family: "Roboto", sans-serif;
  font-weight: 500;
  font-size: 18px;
  color: #000000;
  letter-spacing: 0;
  line-height: 21px;
`;
export const DateIcon = styled.img``;
export const DateTitle = styled.div`
  width: 100px;
`;
export const DateValue = styled.div`
  padding: 15px 40px;
  background: rgb(242, 242, 242);
  border-radius: 8px;
  min-width: 180px;
  border: 1px solid rgb(206, 206, 206);
  box-shadow: rgba(0, 0, 0, 0.15) 0px 2px 6px;

    `;
export const CheckBoxDiv = styled.div`
    width: max-content;
    text-wrap: nowrap;
    background-color:pink;

`

export const InputCheckBoxTitle = styled.div`
  font-size:16px;
  color:#000000;
  font-family:Roboto;
  font-weight:bold;
  display:inline;
  padding-left:2px;
`

/**constant date */

export const SCChartSliderContainer = styled.div`
    display: flex;
    justify-content:space-between;
    justify-content:center;
    gap:13px;
    align-items:center;
    height:55px
`

export const RadioGroup = styled.div`
    display:flex;
    min-width: 200px;
`

export const SelectGroup = styled.div`
    display:flex;
    gap: 20px;
`

export const ChartHeaderRadioGroup = styled.div<{ theme: string }>`
    display:flex;
    align-items:center;
    justify-content:center;
    accent-color:${(props) => globalStyles.chooseThemeColor[props.theme].color5};
    font-style:normal;
    font-variant:normal;
    font-weight:300;
    font-size:14px;
    line-height:19px;
    font-family:Roboto;
`