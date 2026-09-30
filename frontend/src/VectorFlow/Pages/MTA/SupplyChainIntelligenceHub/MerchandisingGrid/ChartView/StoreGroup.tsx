import React, { CSSProperties,useState } from "react";

import {
  CellIconLabel,
  CellIconWrapper,
  FloatingIconPostfix,
  FloatingIconWrapper,
  ViewGridCell,
  ContributionHiddenSection,
  ContributionIcon,
  ContributionWrapper,
  ContributionSection,
  ToolTipWrapper,
  InventoryToolTipContent,
} from "./styles";

import DetailToolTip from "./DetailToolTip";

import Portal from "../../../../../../components/VectorFLOW/layouts/Portal";

import { FloatingStoreDataType } from "../../../.././../types/MCGrid";
import {
  getMCGridStoreIconColor,
  getMCGridStoreImgSrc,
} from "../../../../../../helpers/utils";
import { StoreHoveredIcon, StoreIcon } from "./Icon";
import { useUserData } from "../../../../../../context";

const StoreGroup = (props: { status: string; data: FloatingStoreDataType }) => {
  const { status, data } = props;

  const [isHovered1, setIsHovered1] = useState<boolean>(false);
  const [isHovered2, setIsHovered2] = useState<boolean>(false);

  const [isOpen,toggleToolTip] = useState<boolean>(false)

    const [toolTipPosition,setToolTipPosition] = useState<CSSProperties>()

    const [isDetailToolTipOpen,toggleDetailToolTip] = useState<boolean>(false)


    const onMouseIn = (e:React.MouseEvent<HTMLElement>)=>{
        const {top,left} = e.currentTarget.getBoundingClientRect()
        setToolTipPosition({
            top:top -40,
            left:left
        })
        toggleToolTip(true)
    }

    const onMouseOut = ()=>toggleToolTip(false)

    const onDetailMouseIn =(e:React.MouseEvent<HTMLElement>)=>{
      const {top,left} = e.currentTarget.getBoundingClientRect()
      setToolTipPosition({
          top:top ,
          left:left,
          
      })
      setIsHovered2(true)  
      toggleDetailToolTip(true)  
      
  }

  const onDetailMouseOut = ()=>{
      setIsHovered2(false)
      toggleDetailToolTip(false)
  }

  const [isContributionOpen, setIsContributionOpen] = useState<boolean>(false);

  const { user } = useUserData();

  const themeUI = user.user.theme_ui;

  const inventoryStatus = status==='surplus'?'Pull Out Surplus Inventory':'Require Inventory (Pull In)'

  return (
    <ViewGridCell status={status}>
      <CellIconWrapper
        onMouseEnter={() => setIsHovered1(true)}
        onMouseLeave={() => setIsHovered1(false)}
      >
        {isHovered1 ? (
          <React.Fragment>
            <StoreHoveredIcon value={data.initial["grid-points"]} />
            <CellIconLabel>Store Grid Points</CellIconLabel>
          </React.Fragment>
        ) : (
          <React.Fragment>
            <StoreIcon value={data.initial.stores} />
            <CellIconLabel>Stores</CellIconLabel>
          </React.Fragment>
        )}
      </CellIconWrapper>
      <FloatingIconWrapper
        style={{ border: `solid 1px ${getMCGridStoreIconColor(status)}`,cursor:'pointer' }}
      >
        <CellIconWrapper
            onMouseEnter={onDetailMouseIn}
            onMouseLeave={onDetailMouseOut}
        >
          {isHovered2 ? (
            <React.Fragment>
              <StoreHoveredIcon
                color={getMCGridStoreIconColor(status)}
                value={data.available["grid-points"]}
              />
              <CellIconLabel>Store Grid Points</CellIconLabel>
            </React.Fragment>
          ) : (
            <React.Fragment>
              <StoreIcon
                value={data.available.stores}
                color={getMCGridStoreIconColor(status)}
              />
              <CellIconLabel>Stores</CellIconLabel>
            </React.Fragment>
          )}
        </CellIconWrapper>
        <FloatingIconPostfix onMouseEnter={onMouseIn} onMouseLeave={onMouseOut} src={getMCGridStoreImgSrc(status)} />
      </FloatingIconWrapper>
      <ContributionWrapper
        themeUI={themeUI}
        onMouseEnter={() => setIsContributionOpen(true)}
        onMouseLeave={() => setIsContributionOpen(false)}
      >
        <ContributionSection>{data.contribution} %</ContributionSection>
        <ContributionHiddenSection isOpen={isContributionOpen}>
          <ContributionIcon
            src={
              themeUI === "REGALBLAZE"
                ? "/assets/img/VectorFLOW/BPR/mc-grid-contribution-regal.svg"
                : "/assets/img/VectorFLOW/BPR/mc-grid-contribution.svg"
            }
          />
          <p> Contribution In Overall Gross Margin</p>
        </ContributionHiddenSection>
      </ContributionWrapper>
      {isOpen && (
            <Portal wrapperId="mc-grid">
                <ToolTipWrapper  onMouseLeave={onMouseOut} style={{...toolTipPosition,transform:'translateX(-40%)'}}>
                    <InventoryToolTipContent>
                        {inventoryStatus}
                    </InventoryToolTipContent>
                </ToolTipWrapper>
            </Portal>
        )}
        {(isDetailToolTipOpen && data.available.details)  && (
            <Portal wrapperId="mc-grid">
                <ToolTipWrapper  onMouseLeave={()=>toggleDetailToolTip(false)} style={{...toolTipPosition,transform:'translate(-30%,-100%)'}}>
                    <DetailToolTip data={data.available.details}/>
                </ToolTipWrapper>
            </Portal>
        )}
    </ViewGridCell>
  );
};

export default StoreGroup;
