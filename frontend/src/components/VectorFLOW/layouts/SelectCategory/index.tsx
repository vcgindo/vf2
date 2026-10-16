import { CategoryWrapper, DateContainer, DateWrapper, CardContainer,CardLayout,CardWrapper, TextWrapper, IconWrapper, CountWrapper, CountText, ButtonWrapper, Separator, ButtonComponent, PlanningTaskBar, ButtonFilterWrapper } from "./style";
import VFSelectedFilters from '../../../../components/VectorFLOW/commons/VFSelectedFilters';
import { useState } from 'react'
import VFButton from "../../../../components/VectorFLOW/commons/VFButton";
import { useUserData } from "../../../../context"
import * as globalStyles from '../../../../styles/global'
import { Skeleton } from "../../../../components/commons/styled";
import { LastRunDateHeader } from "../../../../VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/Planning/ActionToolBar/styles";
import MTAVFMultiFilter from "../../../../VectorFlow/Pages/MTA/Common/MTAVFMultiFilter";



interface CountProp {
    businessDate?: string;
    childMonitorCount: number;
    parentMonitorCount: number;
    childExpediteCount: number;
    parentExpediteCount: number;
    reviewExcessInventoryCount: number;
    reviewOrderFulfillmentCount: number;
    onMonitorParentClick: () => void;
    onMonitorChildClick: () => void;
    onExpediteParentClick: () => void;
    onExpediteChildClick: () => void;
    onExcessInventoryReviewClick: () => void;
    onOrderFulfillmentReviewClick: () => void;
    currCategory?: any;
    multiFilter: any
    setMultiFilter: any
    onDelete: any
    onApplyFilter: any
}

const SelectCategory = (props: CountProp) => {

    const {
        childMonitorCount,
        parentMonitorCount,
        parentExpediteCount,
        childExpediteCount,
        reviewExcessInventoryCount,
        reviewOrderFulfillmentCount,
        onMonitorParentClick,
        onMonitorChildClick,
        onExpediteParentClick,
        onExpediteChildClick,
        onExcessInventoryReviewClick,
        onOrderFulfillmentReviewClick,
        multiFilter,
        setMultiFilter,
        onDelete,
        onApplyFilter
    } = props;


    const formattedDate = props.businessDate || 'Loading';

    const [isFilterOpen, toggleFilter] = useState<boolean>(false)

    const { user } = useUserData()
    // const {state:multiFilter,setState:setMultiFilter,onDelete} = useBPRFilter()
    const themeUi = user.user.theme_ui

    const currentTheme = globalStyles.chooseThemeColor[themeUi]

    const handleResetFilters = () => {
        // The modal owns its draft filter state; the page is updated on Apply.
    }

    const handleApplyFilter = (state: any) => {
        setMultiFilter(state)
        onApplyFilter(state)
        toggleFilter(false)
    }

    const getTotalFilterCount = (multiFilter: any) => {
        let total = 0;
        for (const key in multiFilter) {
          if (multiFilter[key]?.filters) {
            total += multiFilter[key].filters.length;
          }
        }
        return total;
      };
     

    return (
        <>


            <PlanningTaskBar>
                <div >
                    <VFSelectedFilters filters={multiFilter} onRemoveFilter={onDelete}></VFSelectedFilters>
                </div>
                <ButtonFilterWrapper>
                    <VFButton onClick={() => toggleFilter(true)} themeUi={themeUi} disabled={false} width={110}>{getTotalFilterCount(multiFilter) > 0 ? "Edit Filter" : "Add Filter"}</VFButton>
                    {
                        isFilterOpen && (
                            <MTAVFMultiFilter
                                isOpen={isFilterOpen}
                                onApply={handleApplyFilter}
                                multiFilter={multiFilter}
                                onClose={() => toggleFilter(false)}
                                onReset={handleResetFilters}
                            />

                        )
                    }
                </ButtonFilterWrapper>
            </PlanningTaskBar>


            <DateContainer>
                <DateWrapper>
                    {formattedDate === "Loading"?(
                        <Skeleton style={{height:30,width:150}}/>
                    ):(
                    <LastRunDateHeader>{formattedDate}</LastRunDateHeader>
                    )}

                </DateWrapper>
                <CategoryWrapper><p>Please select a category</p></CategoryWrapper>
            </DateContainer>

            <CardLayout>
                <CardContainer>
                    <CardWrapper >
                        <IconWrapper><img src={themeUi==="REGALBLAZE"?"/assets/img/VectorFLOW/BPR/monitor-goods-regal.svg":"/assets/img/VectorFLOW/BPR/monitor-goods.svg"} alt="monitor goods in transit/WIP" height="52px" width="52px"></img></IconWrapper>
                        <TextWrapper><b>Monitor Goods In Transit/WIP</b></TextWrapper>
                        <CountWrapper  style={{ color: currentTheme.color4}}>
                            <CountText>{parentMonitorCount}</CountText>
                            <Separator color={currentTheme.color4}></Separator>
                            <CountText>{childMonitorCount}</CountText>
                        </CountWrapper>
                        <ButtonWrapper style={{ backgroundColor: currentTheme.color4}} >
                            <ButtonComponent onClick={onMonitorParentClick}>
                                <button style={{ backgroundColor: currentTheme.color4, color: 'white', font: "inherit" }} >From Parent</button>
                            </ButtonComponent>
                            <Separator color={'white'} ></Separator>
                            <ButtonComponent onClick={onMonitorChildClick}>
                                <button style={{ backgroundColor: currentTheme.color4, color: 'white', font: "inherit" }} >To Child</button>
                            </ButtonComponent>
                        </ButtonWrapper>
                    </CardWrapper>

                    <CardWrapper>
                        <IconWrapper><img src={themeUi==="REGALBLAZE"?"/assets/img/VectorFLOW/BPR/expedite-regal.svg":"/assets/img/VectorFLOW/BPR/expedite.svg"} alt="expedite"></img></IconWrapper>
                        <TextWrapper><b>Expedite</b></TextWrapper>
                        <CountWrapper style={{ color: currentTheme.color4}}>
                            <CountText>{parentExpediteCount}</CountText>
                            <Separator color={currentTheme.color4}></Separator>
                            <CountText>{childExpediteCount}</CountText>
                        </CountWrapper>
                        <ButtonWrapper style={{ backgroundColor: currentTheme.color4}} >
                            <ButtonComponent onClick={onExpediteParentClick}>
                                <button style={{ backgroundColor: currentTheme.color4, color: 'white', font: "inherit" }} >From Parent</button>
                            </ButtonComponent>
                            <Separator color={'white'} ></Separator>
                            <ButtonComponent onClick={onExpediteChildClick}>
                                <button style={{ backgroundColor: currentTheme.color4, color: 'white', font: "inherit" }} >To Child</button>
                            </ButtonComponent>
                        </ButtonWrapper>
                    </CardWrapper>
                </CardContainer>

                <CardContainer>
                    <CardWrapper>
                        <IconWrapper><img src={themeUi==="REGALBLAZE"?"/assets/img/VectorFLOW/BPR/excess-inventory-regal.svg":"/assets/img/VectorFLOW/BPR/excess-inventory.svg"}alt="excess inventory" height="58px" width="55px"></img></IconWrapper>
                        <TextWrapper><b>Excess Inventory</b></TextWrapper>
                        <CountWrapper style={{ color: currentTheme.color4}}>
                            <CountText>{reviewExcessInventoryCount}</CountText>
                            {/* <Separator color={'#BC3D81'}></Separator>
                   <CountText>{totalcount}</CountText>    */}
                        </CountWrapper>
                        <ButtonWrapper style={{ backgroundColor: currentTheme.color4}} >
                            <ButtonComponent onClick={onExcessInventoryReviewClick}>
                                <button style={{ backgroundColor:currentTheme.color4, color: 'white', font: "inherit" }} >Review</button>
                            </ButtonComponent>
                        </ButtonWrapper>
                    </CardWrapper>

                    <CardWrapper>
                        <IconWrapper><img src={themeUi==="REGALBLAZE"?"/assets/img/VectorFLOW/BPR/order-fulfillment-regal.svg":"/assets/img/VectorFLOW/BPR/order-fulfillment.svg"} alt="order fulfillment" height="52px" width="74px"></img></IconWrapper>
                        <TextWrapper><b>Order Fulfillment</b></TextWrapper>
                        <CountWrapper style={{ color: currentTheme.color4}}>
                            <CountText>{reviewOrderFulfillmentCount}</CountText>
                            {/* <Separator color={'#BC3D81'}></Separator>
                   <CountText>{totalcount}</CountText>    */}
                        </CountWrapper>
                        <ButtonWrapper style={{ backgroundColor: currentTheme.color4}} >
                            <ButtonComponent onClick={onOrderFulfillmentReviewClick}>
                                <button style={{ backgroundColor: currentTheme.color4, color: 'white', font: "inherit" }} >Review</button>
                            </ButtonComponent>
                        </ButtonWrapper>
                    </CardWrapper>

                </CardContainer>
            </CardLayout>

        </>
    )
}

export default SelectCategory;

// <CardContainer>
// {
//     currCategory==="GITFromParent" || currCategory==="GITToChild" && (
//         <CardWrapper >
//         <IconWrapper><img src="/assets/img/VectorFLOW/BPR/monitor-goods.svg" alt="monitor goods in transit/WIP" height="52px" width="52px"></img></IconWrapper>
//         <TextWrapper><b>Monitor Goods In Transit/WIP</b></TextWrapper>
//         <CountWrapper>
//            <CountText>{parentMonitorCount}</CountText>
//            <Separator color={'#BC3D81'}></Separator>
//            <CountText>{childMonitorCount}</CountText>
//         </CountWrapper>
//         <ButtonWrapper>
//             <ButtonComponent>
//              <button style={{backgroundColor:'#BC3D81',color:'white', font:"inherit"}} onClick={onMonitorParentClick}>From Parent</button>
//             </ButtonComponent>
//             <Separator color={'white'} ></Separator>
//             <ButtonComponent>
//             <button style={{backgroundColor:'#BC3D81',color:'white', font:"inherit"}} onClick={onMonitorChildClick}>To Child</button>
//             </ButtonComponent>
//         </ButtonWrapper>
//     </CardWrapper>
//     )
// }
// {
// currCategory==="ExpediteFromParent" || currCategory==="ExpediteToChild"&&(
//     <CardWrapper>
//     <IconWrapper><img src="/assets/img/VectorFLOW/BPR/expedite.svg" alt="expedite"></img></IconWrapper>
//     <TextWrapper><b>Expedite</b></TextWrapper>
//     <CountWrapper>
//        <CountText>{parentExpediteCount}</CountText>
//        <Separator color={'#BC3D81'}></Separator>
//        <CountText>{childExpediteCount}</CountText>
//     </CountWrapper>
//     <ButtonWrapper>
//         <ButtonComponent>
//          <button style={{backgroundColor:'#BC3D81',color:'white', font:"inherit"}} onClick={onExpediteParentClick}>From Parent</button>
//         </ButtonComponent>
//         <Separator color={'white'} ></Separator>
//         <ButtonComponent>
//         <button style={{backgroundColor:'#BC3D81',color:'white', font:"inherit"}} onClick={onExpediteChildClick}>To Child</button>
//         </ButtonComponent>
//     </ButtonWrapper>
// </CardWrapper>
// )
// }
//  </CardContainer>


// <CardContainer>
// {
// currCategory==="ExcessInventory" && (
//     <CardWrapper>
//     <IconWrapper><img src="/assets/img/VectorFLOW/BPR/excess-inventory.svg" alt="excess inventory" height="58px" width="55px"></img></IconWrapper>
//     <TextWrapper><b>Excess Inventory</b></TextWrapper>
//     <CountWrapper>
//        <CountText>{reviewExcessInventoryCount}</CountText>
//        {/* <Separator color={'#BC3D81'}></Separator>
//        <CountText>{totalcount}</CountText>    */}
//     </CountWrapper>
//     <ButtonWrapper>
//         <ButtonComponent>
//         <button style={{backgroundColor:'#BC3D81',color:'white', font:"inherit"}} onClick={onExcessInventoryReviewClick}>Review</button>
//         </ButtonComponent>
//     </ButtonWrapper>
// </CardWrapper>
// )
// }
// {
// currCategory==="OrderFulfillment" && (
//     <CardWrapper>
//     <IconWrapper><img src="/assets/img/VectorFLOW/BPR/order-fulfillment.svg" alt="order fulfillment" height="52px" width="74px"></img></IconWrapper>
//     <TextWrapper><b>Order Fulfillment</b></TextWrapper>
//     <CountWrapper>
//        <CountText>{reviewOrderFulfillmentCount}</CountText>
//        {/* <Separator color={'#BC3D81'}></Separator>
//        <CountText>{totalcount}</CountText>    */}
//     </CountWrapper>
//     <ButtonWrapper>
//         <ButtonComponent>
//         <button style={{backgroundColor:'#BC3D81',color:'white', font:"inherit"}} onClick={onOrderFulfillmentReviewClick}>Review</button>
//         </ButtonComponent>
//     </ButtonWrapper>
// </CardWrapper>
// )
// }
// </CardContainer>
