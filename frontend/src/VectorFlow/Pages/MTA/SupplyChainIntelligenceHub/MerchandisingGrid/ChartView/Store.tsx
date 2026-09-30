import React, { CSSProperties,useState } from "react";

import {
  CellIconLabel,
  CellIconWrapper,
  ContributionHiddenSection,
  ContributionIcon,
  ContributionSection,
  ContributionWrapper,
  FloatingIconPostfix,
  FloatingIconWrapper,
  InventoryToolTipContent,
  ToolTipWrapper,
  ViewGridCell,
} from "./styles";

import {
  DefaultStoreDataType,
} from "../../../.././../types/MCGrid";
import {
  getMCGridStoreIconColor,
  getMCGridStoreImgSrc,
} from "../../../../../../helpers/utils";
import { StoreHoveredIcon, StoreIcon } from "./Icon";
import { useUserData } from "../../../../../../context";
import Portal from "../../../../../../components/VectorFLOW/layouts/Portal";
import DetailToolTip from "./DetailToolTip";

interface StoreProps {
  type?: "floating" | "default" | "grouped";
  data: DefaultStoreDataType;
  status: string;
}

const Store = (props: StoreProps) => {
  const { type = "default", status, data } = props;

    const [toolTipPosition,setToolTipPosition] = useState<CSSProperties>()

  const [isHovered, setIsHovered] = useState<boolean>(false);

  const [isContributionOpen, setIsContributionOpen] = useState<boolean>(false);

  const [isInventoryToolTipOpen,toggleInventoryToolTip] = useState<boolean>(false)

  const [isDetailToolTipOpen,toggleDetailToolTip] = useState<boolean>(false)

  const { user } = useUserData();

  const themeUI = user.user.theme_ui;

  const onMouseIn = (e:React.MouseEvent<HTMLElement>)=>{
    const {top,left} = e.currentTarget.getBoundingClientRect()
    setToolTipPosition({
        top:top -40,
        left:left,
        
    })
    toggleInventoryToolTip(true)    
    }
    const onDetailMouseIn =(e:React.MouseEvent<HTMLElement>)=>{
        const {top,left} = e.currentTarget.getBoundingClientRect()
        setToolTipPosition({
            top:top ,
            left:left,
            
        })
        setIsHovered(true)  
        toggleDetailToolTip(true)  
        
    }
    const onMouseOut = ()=>toggleInventoryToolTip(false)

    const onDetailMouseOut = ()=>{
        setIsHovered(false)
        toggleDetailToolTip(false)
    }

  const inventoryStatus = status==='surplus'?'Pull Out Surplus Inventory':'Require Inventory (Pull In)'

  if (type === "floating") {
    return (
      <ViewGridCell status={status}>
        <FloatingIconWrapper
          style={{ border: `solid 1px ${getMCGridStoreIconColor(status)}`,cursor:'pointer' }}
        >
          <CellIconWrapper
            onMouseEnter={onDetailMouseIn}
            onMouseLeave={onDetailMouseOut}
          >
            {isHovered ? (
              <React.Fragment>
                <StoreHoveredIcon
                  color={getMCGridStoreIconColor(status)}
                  value={data["grid-points"]}
                />
                <CellIconLabel>Store Grid Points</CellIconLabel>
              </React.Fragment>
            ) : (
              <React.Fragment>
                <StoreIcon
                  value={data.stores}
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
            <p>Contribution In Overall Gross Margin</p>
          </ContributionHiddenSection>
        </ContributionWrapper>
        {isInventoryToolTipOpen && (
            <Portal wrapperId="mc-grid">
                <ToolTipWrapper  onMouseLeave={onMouseOut} style={{...toolTipPosition,transform:'translateX(-40%)'}}>
                    <InventoryToolTipContent>
                        {inventoryStatus}
                    </InventoryToolTipContent>
                </ToolTipWrapper>
            </Portal>
        )}
        {(isDetailToolTipOpen && data.details) && (
            <Portal wrapperId="mc-grid">
                <ToolTipWrapper  onMouseLeave={()=>toggleDetailToolTip(false)} style={{...toolTipPosition,transform:'translate(-30%,-100%)'}}>
                    <DetailToolTip data={data.details}/>
                </ToolTipWrapper>
            </Portal>
        )}
      </ViewGridCell>
    );
  }
  return (
    <ViewGridCell status={status}>
      <CellIconWrapper
        style={{cursor:'pointer'}}
       onMouseEnter={onDetailMouseIn}
       onMouseLeave={onDetailMouseOut}
      >
        {isHovered ? (
          <React.Fragment>
            <StoreHoveredIcon value={data["grid-points"]} />
            <CellIconLabel>Store Grid Points</CellIconLabel>
          </React.Fragment>
        ) : (
          <React.Fragment>
            <StoreIcon value={data.stores} />
            <CellIconLabel>Stores</CellIconLabel>
          </React.Fragment>
        )}
      </CellIconWrapper>
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
      {(isDetailToolTipOpen && data.details)  && (
            <Portal wrapperId="mc-grid">
                <ToolTipWrapper  onMouseLeave={()=>toggleDetailToolTip(false)} style={{...toolTipPosition,transform:'translate(-30%,-100%)'}}>
                    <DetailToolTip data={data.details}/>
                </ToolTipWrapper>
            </Portal>
        )}
    </ViewGridCell>
  );
};

export default Store;
