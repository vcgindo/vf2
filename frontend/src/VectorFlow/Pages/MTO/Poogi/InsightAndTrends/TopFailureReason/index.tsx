import { Allotment } from "allotment";
import { useEffect, useState } from "react";
import useViewPort from "../../../../../../hooks/useViewPort";
import MTOActionToolBar from "../../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar";
import OTIFFailureGraph from "./OTIFFailureGraph";
import {
  BTRAllomentSection,
  BTRTableWrapper,
  HorizontalViewWrapper,
} from "./styles";
import OverlayLoader from '../../../Common/Loader';
import { notifyError, notifySuccess } from '../../../../../../helpers/notify';
import TagCellToolTip from "../../../Poogi/InsightAndTrends/OTIFAnalysis/TagCellRenderer/TagCellRenderer";
import { useTopFailureData } from "../../../../../../VectorFlow/Services/MTO/Poogi/InsightAndTrends/TopFailureReasons";
import GridView from "../../../Common/GridView";

import { useGetUserUIConfigData, useUpdateUserUIConfigData } from '../../../../../../VectorFlow/Services/MTO/Common/UserUIConfig'
import { useGetUIConfigData } from '../../../../../Services/MTO/Common/UIConfig';
import { getColumnDefinations } from '../../../../../../helpers/utils';
import { FilterPageName, pagination, UIGridCode } from "../../../Common/Enum";
import { useUserData } from "../../../../../../context/index";
import useFilter from '../../../../../../hooks/useFilter'
import { useGetFilterData } from '../../../../../../VectorFlow/Services/MTO/Common/CommonFilter'
import BPPRenderer from "../../../Common/BPRRenderer/BPPRenderer";
import { format } from "date-fns";
import { useGetDate } from "../../../../../../VectorFlow/Services/MTO/Production/InsightsAndTrends/RMPMExpediting";


const APIFilterConfig = {
    filSecVisConfig: {
      "Poogi_Top_Failure_Reasons" : {
        mjr : true,
        or: true,
        res: true,
        cus: true
      },
    }
};
const TopFailureReasons = () => {
  const [isGridView, setIsGridView] = useState(false);
  const { screenHeight } = useViewPort();
  const { mutateAsync: getTopFailureData, isLoading, isError, isSuccess } = useTopFailureData();
  const [graphData, setGraphData] = useState<any>({});
  const [currentGridRef, setCurrentGridRef] = useState<any>(null);
  const [columnState, setColumnState] = useState<any>([]);
  const [isReset, setIsReset] = useState(false);
  const [colDef, setColDef] = useState([{}]);
  const [HeaderData, setHeaderData] = useState([]);
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
  } = useFilter(filterData, APIFilterConfig.filSecVisConfig.Poogi_Top_Failure_Reasons);
  const { mutateAsync: updateUserUIReportConfigData, isLoading: isUpdateUserConfig } = useUpdateUserUIConfigData();
  const { mutateAsync: getUserUIReportConfigData, isLoading: isGetUserConfig } = useGetUserUIConfigData();
  const { mutateAsync: getUIConfigData } = useGetUIConfigData()
  const { user } = useUserData();
  const [masterUIConfig, setMasterUIConfig] = useState([]);
  const [userPageSize, setUserPageSize] = useState<number>();
  const [userConfigFetched, setUserConfigFetched] = useState(false);

  const reportName = "TopFailureReasons";

  const { data: apiResponseData } = useGetDate();
 
  const lastRunDate = new Date(apiResponseData?.data?.data).toString() !== "Invalid Date" ? format(new Date(apiResponseData?.data?.data), 'dd MMM yyyy') : '';

  const colDefCustomizations = {
    tag: {
      tooltipValueGetter: (params: any) => params.value,
      cellRenderer: TagCellToolTip,
      cellStyle: {
        display: 'flex',
        justifyContent: "center",
      },
      minWidth:100,
    },
    bpp: {
      cellRenderer: BPPRenderer,
      minWidth:100,
    },
  }

  const getGraphData = async (params: any) => {
    try {
      const response = await getTopFailureData({...params});
      setGraphData(response.data.data);
    }
    catch (e) {
      console.log(e);
      notifyError('Failed to fetch Graph data!');
    }
  }

  useEffect(() => {
    getGraphData({ graphflag: 1 });
  }, []);

  useEffect(() => {
    if (isSuccess) {
      notifySuccess("Fetched Data successfully!")
    }
    if (isError) {
      notifyError("Failed to load data!")
    }
  }, [isSuccess, isError])

  
  const getUserColumnConfig = async () => {
    try {
      const data = await getUserUIReportConfigData({
        un: user.user.name,
        rn_id: UIGridCode.PoogiTopFailureReason
      });

      setUserConfigFetched(true);
           const newConfig = data?.data?.data[0] ? JSON.parse(data?.data?.data[0]?.columns_settings) || [] : [];
           setUserPageSize(newConfig.pageSize ? Number(newConfig.pageSize) : pagination.mtoPageSize);
           setColumnState(newConfig.cs);

      if (!data) {
        console.error('Failed to apply column state');
      }
    } catch (error) {
      console.error(error);
    }
  }

  const setColumnDef = async () => {
    try {
      const response = await getUIConfigData(reportName);
      setHeaderData(response?.data?.data);
    }
    catch (e) {
      console.log(e);
    }
  }

    const handleSaveClick = async (coldefs?: any, page_size?: number) => {
      try {
          if (coldefs) {
              const fullConfig = { 
                  cs: coldefs, 
                  pageSize: userPageSize 
              };
              const payload = {
                  un: user.user.name,
                  rn_id: UIGridCode.PoogiTopFailureReason,
                  cs: JSON.stringify(fullConfig),
              };
              await updateUserUIReportConfigData([payload]);
              setColumnState([...coldefs]);
          } 
          else if (page_size) {
              const config = columnState;
              const fullConfig = { cs: config, pageSize: page_size };
              const payload = {
                  un: user.user.name,
                  rn_id: UIGridCode.PoogiTopFailureReason,
                  cs: JSON.stringify(fullConfig),
              };
              
              await updateUserUIReportConfigData([payload]);
          }
          else {
              if (currentGridRef?.current?.api) {
                  const config = currentGridRef.current.api.getColumnState();
                  const fullConfig = { cs: config, pageSize: userPageSize };
                  
                  const payload = {
                      un: user.user.name,
                      rn_id: UIGridCode.PoogiTopFailureReason,
                      cs: JSON.stringify(fullConfig)
                  };
                  await updateUserUIReportConfigData([payload]);
                  await getUserColumnConfig();
              }
          }
      } catch (error) {
          console.error(error);
      }
  }

  const handleResetClick = () => {
    setIsReset(true);
  }

  const getFilterData = async () => {
    try {
      const response = await getPageWiseFilterData({page_name: FilterPageName.Poogi_Top_Failure_Reasons});
      setFilterData(response?.data.data);
    } catch (error) {
      console.error(error);
    }
  }

  useEffect(() => {
    setColDef(getColumnDefinations(HeaderData, colDefCustomizations))
  }, [HeaderData])

  useEffect(() => {
    setColumnDef();
    getFilterData();
  }, [])


  useEffect(() => {
    if (isReset) {
      handleSaveClick(masterUIConfig);
      setIsReset(false);
    }
  }, [isReset]);

  useEffect(() => {
    if (currentGridRef?.current) {
      setMasterUIConfig(currentGridRef?.current.api.getColumnState());
      getUserColumnConfig();
    }
  }, [colDef, currentGridRef]);

  const themeUi = user?.user?.theme_ui;

  return (
    <div>
      {
        (isLoading || isUpdateUserConfig || isGetUserConfig) && <OverlayLoader />
      }
      <MTOActionToolBar
        isGridView={isGridView}
        setIsGridView={setIsGridView}
        themeUi={themeUi}
        isChartGridToggle 
        isAddFilterButton
        handleSaveClick={handleSaveClick}
        handleResetClick={handleResetClick}
        isFilterOpen={isFilterOpen}
        onAddFilter={onAddFilter}
        toggleFilter={toggleFilter}
        onApplyFilter={onApplyFilter}
        multiFilter={currFilter}
        setMultiFilter={setCurrFilter}
        onFilterRemove={onFilterRemove}
        isMfgSelected={isMfgSelected}
      />
      <HorizontalViewWrapper style={{ marginTop: "20px", marginLeft: '15px' }}>
        {isGridView ? (
          <GridView
            getData={(params: any) => getTopFailureData({...params})}
            isLoading={isLoading}
            isError={isError}
            isSuccess={isSuccess}
            colDef={colDef}
            setCurrentGridRef={setCurrentGridRef}
            currentGridRef={currentGridRef}
            columnState={columnState}
            appliedFilters={appliedFilters}
            userPageSize={userPageSize}
            setUserPageSize={setUserPageSize}
            handleSaveClick={handleSaveClick}
            userConfigFetched={userConfigFetched}
          />
        ) : (
          <BTRTableWrapper style={{ height: screenHeight - 190, margin: "0" }}>
            <Allotment vertical={false} separator={false}>
              <Allotment.Pane preferredSize={"50%"}>
                <BTRAllomentSection>
                  <OTIFFailureGraph month="previous" graphData={graphData.m1} lastRunDate={lastRunDate} subtractStartMonths={1} subtractEndMonths={2}/>
                </BTRAllomentSection>
              </Allotment.Pane>
              <Allotment.Pane preferredSize={"50%"}>
                <BTRAllomentSection>
                  <OTIFFailureGraph month="current" graphData={graphData.m2} lastRunDate={lastRunDate}  subtractStartMonths={0}  subtractEndMonths={1} />
                </BTRAllomentSection>
              </Allotment.Pane>
            </Allotment>
          </BTRTableWrapper>
        )}
      </HorizontalViewWrapper>
    </div>
  );
};
export default TopFailureReasons;
