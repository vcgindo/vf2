import { VFPaginationProps } from "../../../../../../components/VectorFLOW/commons/VFPagination";
import ExcessInventoryGrid from "../ExcessInventory/Grid";
import ExpediteParentCreateAvailabilityAtParentGrid from "../Expedite/Parent/Grid/CreateAvailabilityAtParent";
import ExpediteParentExpediteDispatchesGrid from "../Expedite/Parent/Grid/ExpediteDispatches";
import ExpediteChildExpediteDispatchesGrid from "../Expedite/Child/Grid/ExpediteDispatches";
import MonitorGITChildLocationWiseGrid from "../MonitorGoodsInTransit/Child/Grid/LocationWise"
import MonitorGITChildTransporterWiseGrid from "../MonitorGoodsInTransit/Child/Grid/TransporterWise"
import MonitorGITParent from "../MonitorGoodsInTransit/Parent";
import OrderFulfillmentGrid from '../OrderFulfillment/Grid';
import ExcessInventoryCustomCharts from "../ExcessInventory/Grid/Custom";
import OrderFulfillmentCustomCharts from "../OrderFulfillment/Grid/Custom";
import ExpediteChildCustomCharts from "../Expedite/Child/Grid/Custom";
import MonitorGITChildCustomCharts from "../MonitorGoodsInTransit/Child/Grid/Custom";



interface GridViewProps {
    category:string,
    currentTab:string,
    currentGridData:any,
    paginationProps:VFPaginationProps,
    onOpenDailyDataGraph:any,
    planningCounts?:any

}
const GridView = ({category,currentTab,currentGridData,paginationProps,onOpenDailyDataGraph,planningCounts}:GridViewProps) => {
    const renderGrid = ()=>{
        switch (category) {
            case 'GITFromParent':
            return (
                <MonitorGITParent
                data={currentGridData}
                paginationProps={paginationProps}
                onOpenDailyDataGraph={onOpenDailyDataGraph}
                currentCategory={category}
                currentTab={currentTab}
                />
            );
            case 'GITToChild':
            if (currentTab === 'custom') {
                return <MonitorGITChildCustomCharts recordCount={planningCounts.childMonitorCustomCount} />;
            } else if (currentTab === 'locationWise') {
                return (
                    <MonitorGITChildLocationWiseGrid
                        data={currentGridData ? currentGridData['locationWise'] : ['']}
                        paginationProps={paginationProps}
                        onOpenDailyDataGraph={onOpenDailyDataGraph}
                        currentCategory={category}
                        currentTab={currentTab}
                    />
                );
            } else {
                return (
                    <MonitorGITChildTransporterWiseGrid
                        data={currentGridData ? currentGridData['transporterWise'] : []}
                        paginationProps={paginationProps}
                        onOpenDailyDataGraph={onOpenDailyDataGraph}
                        currentCategory={category}
                        currentTab={currentTab}
                    />
                );
            }
            case 'ExpediteFromParent':
            if (currentTab === 'createAvailabilityAtParent') {
                return (
                <ExpediteParentCreateAvailabilityAtParentGrid
                    data={currentGridData ? currentGridData['createAvailabilityAtParent'] : []}
                    paginationProps={paginationProps}
                    onOpenDailyDataGraph={onOpenDailyDataGraph}
                    currentCategory={category}
                    currentTab={currentTab}
                />
                );
            } else {
                return (
                <ExpediteParentExpediteDispatchesGrid
                    data={currentGridData ? currentGridData['expediteDispatches'] : []}
                    paginationProps={paginationProps}
                    onOpenDailyDataGraph={onOpenDailyDataGraph}
                    currentCategory={category}
                    currentTab={currentTab}
                />
                );
            }
            case 'ExpediteToChild':
            if (currentTab === 'custom') {
                return <ExpediteChildCustomCharts recordCount={planningCounts.childExpediteCustomCount} />;
            } else {
                return (
                <ExpediteChildExpediteDispatchesGrid
                    data={currentGridData ? currentGridData['expediteDispatches'] : []}
                    paginationProps={paginationProps}
                    onOpenDailyDataGraph={onOpenDailyDataGraph}
                    currentCategory={category}
                    currentTab={currentTab}
                />
                );
            }
            case 'ExcessInventory':
            if (currentTab === 'custom') {
                return <ExcessInventoryCustomCharts key={'custom'} recordCount={planningCounts.reviewExcessInventoryCustomCount} />;
            } else {
                return (
                <ExcessInventoryGrid
                    key={'excessInventory'}
                    data={currentGridData ? currentGridData : []}
                    paginationProps={paginationProps}
                    onOpenDailyDataGraph={onOpenDailyDataGraph}
                    currentCategory={category}
                    currentTab={currentTab}
                />
                );
            }
            case 'OrderFulfillment':
            if (currentTab === 'custom') {
                return <OrderFulfillmentCustomCharts recordCount={planningCounts.reviewOrderFulfillmentCustomCount} />;
            } else {
                return (
                <OrderFulfillmentGrid
                    data={currentGridData ? currentGridData : []}
                    paginationProps={paginationProps}
                    onOpenDailyDataGraph={onOpenDailyDataGraph}
                    currentCategory={category}
                    currentTab={currentTab}
                />
                );
            }
            default:
            return <></>;
        }

    }
    
    return(
        <>
            {renderGrid()}
        </>
    )
    
}

export default GridView;