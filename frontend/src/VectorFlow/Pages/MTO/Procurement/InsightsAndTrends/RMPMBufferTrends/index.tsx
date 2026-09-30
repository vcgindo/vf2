
import { Allotment } from "allotment"
import { useEffect, useState } from "react"
import MTOActionToolBar from "../../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar"
import BTMTA from "./BTMTA"
import BTMTO from "./BTMTO"
import { BTRAllomentSection, BTRTableWrapper, HorizontalViewWrapper } from "./styles"
import "./style.css"
import { useGetRMPMBufferTrendsData } from "../../../../../../VectorFlow/Services/MTO/Procurement/RMPMBufferTrends"
import { BufferTrendData } from "../../../../../../types/MTO/types"
import { toast } from "react-toastify"
import { notifyError, notifyLoader, notifySuccess } from "../../../../../../helpers/notify"
import { useUserData } from "../../../../../../context"
import { useGetFilterData } from '../../../../../..//VectorFlow/Services/MTO/Common/CommonFilter';
import useFilter from '../../../../../../hooks/useFilter';
import { FilterPageName } from "../../../Common/Enum";
import { formatFilterJSON } from "../../../../../../helpers/utils"
import { useGetDate } from "../../../../../../VectorFlow/Services/MTO/Production/InsightsAndTrends/RMPMExpediting"

const APIFilterConfig = {
    filSecVisConfig: {
        "Proc_RM_PM_BufferTrend" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
    }
};


const RMPMBufferTrends = () => {
    const [filterData, setFilterData] = useState({});
    const { mutateAsync: getPageWiseFilterData, /*isLoading*/ } = useGetFilterData()
    const { 
        state: currFilter, 
        setState: setCurrFilter, 
        onFilterRemove, 
        isFilterOpen, 
        isMfgSelected,
        onAddFilter, 
        onApplyFilter,
        appliedFilters, 
        toggleFilter 
      } = useFilter(filterData, APIFilterConfig.filSecVisConfig.Proc_RM_PM_BufferTrend);


    const formatDate = (date: Date): string => {
        // console.log("dateddd", date)
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        return `${day}-${month}-${year}`;
    }

    const { user } = useUserData();
    const themeUi = user?.user?.theme_ui;
    const { data: apiResponseData, /*isLoading, refetch*/ } = useGetDate();

    const lastRunDate = apiResponseData?.data?.data;

    const convertToGraphData = (apiData: any, lastRunDate?:Date,) => {
        try {
            const startDate = formatDate(new Date(lastRunDate ?? Date.now()));
            const numDays = 90;
            const updatedData: BufferTrendData[] = [];
            const dateParts = startDate?.split('-');
            const date = new Date(`${dateParts[2]}-${dateParts[1]}-${dateParts[0]}`); // Convert to YYYY-MM-DD

            for (let i = 0; i < numDays; i++) {
                const day = formatDate(date);
                let entry: any = {
                    'dt': day,
                    'b': 0,
                    'r': 0,
                    'g': 0,
                    'y': 0,
                    'bl': 0,
                    'w': 0,
                };
                const newDate = day?.split('-')?.reverse()?.join('-');

                if (apiData[newDate]) {
                    if (apiData[newDate]?.B) {
                        entry = { ...entry, b: apiData[newDate]?.B || 0 }
                    }
                    if (apiData[newDate]?.R) {
                        entry = { ...entry, r: apiData[newDate]?.R || 0 }
                    }
                    if (apiData[newDate]?.G) {
                        entry = { ...entry, g: apiData[newDate]?.G || 0 }
                    }
                    if (apiData[newDate]?.Y) {
                        entry = { ...entry, y: apiData[newDate]?.Y || 0 }
                    }
                    if (apiData[newDate]?.W) {
                        entry = { ...entry, w: apiData[newDate]?.W || 0 }
                    }
                    if (apiData[newDate]?.Bl) {
                        entry = { ...entry, bl: apiData[newDate]?.Bl || 0 }
                    }
                }




                updatedData.push(entry);
                date.setDate(date.getDate() - 1);
                // date = date?.split('-')?.reverse()?.join('-')


            }
            return updatedData;
        }
        catch (e) {
            console.log("this is the error", e)
        }
    }

    const [isMTO] = useState(true);

    const { mutateAsync: getRMPMBufferTrendsData } = useGetRMPMBufferTrendsData();

    const [MTOData, setMTOData] = useState<any>([]);
    const [MTAData, setMTAData] = useState<any>([]);
    const GetData = async () => {
        try {
            toast.dismiss();
            notifyLoader("Loading Graph Data ...")
            const formatedFilters = formatFilterJSON(appliedFilters);
            const APIData = await getRMPMBufferTrendsData({appliedFilters: formatedFilters});
            const updatedDataMTO = convertToGraphData(APIData?.data?.data.MTO,lastRunDate);
            const updatedDataMTA = convertToGraphData(APIData?.data?.data.MTA,lastRunDate);
            // console.log('==>', updatedDataMTA)
            setMTOData(updatedDataMTO);
            setMTAData(updatedDataMTA);
            toast.dismiss();
            notifySuccess("Grid Data fetched successfully!");
        }
        catch (e) {
            toast.dismiss();
            notifyError("Failed to fetch data");
        }

    }

    const getFilterData = async () => {
    try {
        const response = await getPageWiseFilterData({page_name: FilterPageName.Proc_RM_PM_BufferTrend});
        setFilterData(response?.data.data);
    } catch (error) {
        console.error(error);
    }
    }

    useEffect (() => {
        if(Object.entries(appliedFilters).length){
          GetData();
        }
      }, [appliedFilters])



    useEffect(() => {
        getFilterData()
    }, [])


    return (
        <div style={{ height: "90%", marginLeft: '20px', paddingTop: "20px" }}>

            <MTOActionToolBar 
                comp={"BTRMTO"} 
                themeUi={themeUi}
                isAddFilterButton 
                isFilterOpen={isFilterOpen}
                onAddFilter={onAddFilter}
                toggleFilter={toggleFilter}
                onApplyFilter={onApplyFilter}
                multiFilter={currFilter}
                setMultiFilter={setCurrFilter}
                onFilterRemove={onFilterRemove}
                isMfgSelected={isMfgSelected}
            />
            <HorizontalViewWrapper>
                <BTRTableWrapper>
                    {
                        (isMTO) ?
                            (<Allotment vertical={false} separator={false}   >
                                <Allotment.Pane minSize={460} preferredSize={'50%'}>
                                    <BTRAllomentSection>
                                        <BTMTO data={MTOData} isMTO={isMTO} lastRunDate={lastRunDate} />
                                    </BTRAllomentSection>
                                </Allotment.Pane>

                                <Allotment.Pane minSize={460} preferredSize={'50%'}>
                                    <BTRAllomentSection>
                                        <BTMTA data={MTAData} isMTO={isMTO} lastRunDate={lastRunDate} />
                                    </BTRAllomentSection>
                                </Allotment.Pane>
                            </Allotment>)
                            :
                            <BTMTO data={MTOData} isMTO={isMTO} lastRunDate={lastRunDate} />

                    }
                </BTRTableWrapper>

            </HorizontalViewWrapper>
        </div>
    )
}
export default RMPMBufferTrends
