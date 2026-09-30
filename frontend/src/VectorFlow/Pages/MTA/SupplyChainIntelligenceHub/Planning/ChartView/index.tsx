import MonitorGITChildLocationWiseCharts from "../MonitorGoodsInTransit/Child/Charts/LocationWise";
import MonitorGITChildTransporterWiseCharts from '../MonitorGoodsInTransit/Child/Charts/TransporterWise';
import MonitorGITParent from "../MonitorGoodsInTransit/Parent";
import ExpediteDispatches from '../Expedite/Parent/Chart/ExpediteDispatches';
import ExpediteDispatchesChild from "../Expedite/Child/Chart/ExpediteDispatches";
import CreateAvailabilityAtParent from "../Expedite/Parent/Chart/CreateAvailabilityAtParent";
import ExcessInventoryLocation from "../ExcessInventory/Chart/ExcessInventoryLocationWise";
import ExcessInventoryProduct from "../ExcessInventory/Chart/ExcessInventoryProductWise";
import OrderFulfillmentLocation from '../OrderFulfillment/Chart/OrderFulfillmentLocationWise';
import OrderFulfillmentProduct from '../OrderFulfillment/Chart/OrderFulfillmentProductWise';
import { VFPaginationProps } from "../../../../../../components/VectorFLOW/commons/VFPagination";
import {PlanningCounts} from '../../../../../types/MTA'


interface ChartViewProps {
    category:string,
    currentTab:string,
    currentGraphData:any,
    planningCounts:PlanningCounts
    paginationProps:VFPaginationProps,
    onOpenDailyDataGraph:any

}
const ChartView = ({category,currentTab,currentGraphData,paginationProps,onOpenDailyDataGraph,planningCounts}:ChartViewProps) => {
    const renderGraphs = ()=>{
        switch(category){
            case 'GITFromParent':
                return <MonitorGITParent data={currentGraphData?currentGraphData : []} paginationProps={paginationProps} onOpenDailyDataGraph={onOpenDailyDataGraph} currentCategory={category} currentTab={currentTab}/>
            case 'GITToChild':
                if(currentTab === 'locationWise'){
                    return (
                        <MonitorGITChildLocationWiseCharts
                            data={currentGraphData ? currentGraphData['locationWise']:[]}
                        />
                    )
                }
                if(currentTab === 'transporterWise'){
                    return (
                        <MonitorGITChildTransporterWiseCharts
                            data={currentGraphData ? currentGraphData['transporterWise']:[]}
                        />
                    )
                }
                break;
            case 'ExpediteFromParent':
                if(currentTab === 'expediteDispatches'){
                    return (
                        <ExpediteDispatches
                            data={currentGraphData ? currentGraphData['expediteDispatches']:[]}
                        />
                    )
                }
                if(currentTab === 'createAvailabilityAtParent'){
                    return (
                        <CreateAvailabilityAtParent
                            data={currentGraphData ? currentGraphData['createAvailabilityAtParent']:[]}
                        />
                    )
                }
                break; 
            case 'ExpediteToChild':
                if(currentTab === 'expediteDispatches'){
                    return (
                        <ExpediteDispatchesChild
                            data={currentGraphData ? currentGraphData['expediteDispatches']:[]}
                        />
                    )
                }
                break;   
            case 'ExcessInventory':
                if(currentTab === 'excessInventoryLocation'){
                    return (
                        <ExcessInventoryLocation
                            data={currentGraphData ? currentGraphData:[]}
                        />
                    )
                }
                if(currentTab === 'excessInventoryProduct'){
                    return (
                        <ExcessInventoryProduct
                            data={currentGraphData ? currentGraphData:[]}
                        />
                    )
                }
                break;
            case 'OrderFulfillment':
                if(currentTab === 'orderFulfillmentLocation'){
                    return (
                        <OrderFulfillmentLocation
                            data={currentGraphData ? currentGraphData:[]}
                        />
                    )
                }
                if(currentTab === 'orderFulfillmentProduct'){
                    return (
                        <OrderFulfillmentProduct
                            data={currentGraphData ? currentGraphData:[]}
                        />
                    )
                }
                break;
            default:
                return <></>
        }

    }
    
    return(
        <>
            {renderGraphs()}
        </>
    )
    
}

export default ChartView;