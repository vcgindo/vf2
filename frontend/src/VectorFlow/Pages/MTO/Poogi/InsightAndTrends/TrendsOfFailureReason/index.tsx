import { Allotment } from 'allotment'
import { useEffect, useState } from 'react'
import { useTopFailureReasonData } from '../../../../../../VectorFlow/Services/MTO/Poogi/InsightAndTrends/TrendsOfFailureReason'
import MTOActionToolBar from '../../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar'
import { BTRAllomentSection, BTRTableWrapper, HorizontalViewWrapper } from '../../../Common/SplitGraphContainer/styles'
import DownTrend from './DownTrend'
import EmgAndUnres from './EmgAndUnres'
import OverlayLoader from '../../../Common/Loader';
import { notifyError, notifySuccess } from '../../../../../../helpers/notify';
import useFilter from '../../../../../../hooks/useFilter'
import { useGetFilterData } from '../../../../../../VectorFlow/Services/MTO/Common/CommonFilter'
import { FilterPageName } from '../../../Common/Enum'
import { formatFilterJSON } from '../../../../../../helpers/utils'
import { useUserData } from "../../../../../../context/index";


const APIFilterConfig = {
    filSecVisConfig: {
        "Poogi_Trend_Of_Failure_Reasons" : {
            mjr : true,
            or: true,
            res: true,
            cus: true
        },
    }
};

const TrendsOfFailureReason = () => {

    const [graphData, setGraphData] = useState<any>({});
    const { mutateAsync: getTrendsFailureData, isLoading, isError, isSuccess } = useTopFailureReasonData();
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
        toggleFilter,
        appliedFilters
    } = useFilter(filterData, APIFilterConfig.filSecVisConfig.Poogi_Trend_Of_Failure_Reasons);
  const { user } = useUserData();

    const themeUi = user?.user?.theme_ui;
    const getGraphData = async () => {
        try {
          const formatedFilters = formatFilterJSON(appliedFilters);
          const response = await getTrendsFailureData({ appliedFilters: formatedFilters });
          setGraphData(response.data.data);
        }
        catch (e) {
          console.log(e);
          notifyError('Failed to fetch Graph data!');
        }
    }

    const getFilterData = async () => {
        try {
          const response = await getPageWiseFilterData({page_name: FilterPageName.Poogi_Trend_Of_Failure_Reasons});
          setFilterData(response?.data.data);
        } catch (error) {
          console.error(error);
        }
    }

    useEffect(() => {
        getFilterData();
    }, []);
    
    useEffect(()=>{
        getGraphData();
      },[appliedFilters])
    
      useEffect(() => {
        if (isSuccess) {
          notifySuccess("Fetched Data successfully!")
        }
        if (isError) {
          notifyError("Failed to load data!")
        }
      }, [isSuccess, isError])
      


    return (
        <>
            {
                isLoading && <OverlayLoader />
            }
            <MTOActionToolBar 
                isAddFilterButton
                isFilterOpen={isFilterOpen}
                onAddFilter={onAddFilter}
                toggleFilter={toggleFilter}
                themeUi={themeUi}
                onApplyFilter={onApplyFilter}
                multiFilter={currFilter}
                setMultiFilter={setCurrFilter}
                onFilterRemove={onFilterRemove}
                isMfgSelected={isMfgSelected}
            />
            <HorizontalViewWrapper style={{ margin: '20px 14px', height: '85%', display: 'flex' }}>
                <BTRTableWrapper style={{ flex: '1', margin: '0' }}>
                    <Allotment vertical={false} separator={false}   >
                        <Allotment.Pane minSize={400} preferredSize={'50%'} className='allotment-pane-custom'>
                            <BTRAllomentSection>
                                <EmgAndUnres graphData={graphData?.eu} />
                            </BTRAllomentSection>
                        </Allotment.Pane>
                        <Allotment.Pane minSize={400} preferredSize={'50%'} className='allotment-pane-custom'>
                            <BTRAllomentSection>
                                <DownTrend graphData={graphData?.dt} />
                            </BTRAllomentSection>
                        </Allotment.Pane>
                    </Allotment>
                </BTRTableWrapper>
            </HorizontalViewWrapper>
        </>
    )
}

export default TrendsOfFailureReason