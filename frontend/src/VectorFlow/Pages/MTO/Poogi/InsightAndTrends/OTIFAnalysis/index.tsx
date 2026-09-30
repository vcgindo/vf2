import { Allotment } from "allotment";
import { useEffect, useState } from "react";
import MTOActionToolBar from "../../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar";
import OTIFTrendsGraph from "./OTIFTrendsGraph";
import OTAndIFTrendsGraph from "./OTAndIFTrendsGraph";
import {
  BTRAllomentSection,
  BTRTableWrapper,
  HorizontalViewWrapper,
} from "./styles";
import TagCellToolTip from "./TagCellRenderer/TagCellRenderer";
import { useGetFilterData } from "../../../../../../VectorFlow/Services/MTO/Common/CommonFilter";
import useFilter from "../../../../../../hooks/useFilter";
import { useGetOTIFAnalysisData, useGetOTIFAnalysisDataExcelExport } from "../../../../../../VectorFlow/Services/MTO/Poogi/InsightAndTrends/OTIFAnalysis";
import OverlayLoader from '../../../Common/Loader';
import { notifyError, notifySuccess } from '../../../../../../helpers/notify';
import GridView from "../../../Common/GridView";
import { useGetUserUIConfigData, useUpdateUserUIConfigData } from '../../../../../../VectorFlow/Services/MTO/Common/UserUIConfig'
import { useGetUIConfigData } from '../../../../../Services/MTO/Common/UIConfig';
import { DownloadExcel, formatFilterJSON, getBodyForExcelExport, getColumnDefinations } from '../../../../../../helpers/utils';
import { FilterPageName, pagination, UIGridCode } from "../../../Common/Enum";
import { useUserData } from "../../../../../../context/index";
import useColDef from "../../../../../../hooks/useColDef";
import BPPRenderer from "../../../Common/BPRRenderer/BPPRenderer";
import moment from "moment";

const APIFilterConfig = {
  filSecVisConfig: {
    "Poogi_OTIF_Analysis": {
      mjr: true,
      or: true,
      res: true,
      cus: true
    },
  }
};

const OTIFAnalysis = () => {
  const [isGridView, setIsGridView] = useState(false);
  const { mutateAsync: getOTIFAnalysisData, isLoading, isError, isSuccess } = useGetOTIFAnalysisData()
  const [graphData, setGraphData] = useState<any>({});
  const { mutateAsync: getPageWiseFilterData, /*isLoading*/ } = useGetFilterData()
  const [filterData, setFilterData] = useState({});
  const [currentGridRef, setCurrentGridRef] = useState<any>(null);
  const [columnState, setColumnState] = useState<any>([]);
  const [isReset, setIsReset] = useState(false);
  const [colDef, setColDef] = useState([{}]);
  const [HeaderData, setHeaderData] = useState([]);
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
  } = useFilter(filterData, APIFilterConfig.filSecVisConfig.Poogi_OTIF_Analysis);

  const { mutateAsync: updateUserUIReportConfigData, isLoading: isUpdateUserConfig } = useUpdateUserUIConfigData();
  const { mutateAsync: getUserUIReportConfigData, isLoading: isGetUserConfig } = useGetUserUIConfigData();
  const { mutateAsync: getUIConfigData } = useGetUIConfigData()
  const { user } = useUserData();
  const { mutateAsync: getOTIFAnalysisDataExcelExport } = useGetOTIFAnalysisDataExcelExport();
  const { colDefMap, getColDef } = useColDef();
  const [masterUIConfig, setMasterUIConfig] = useState([]);

  const [userPageSize, setUserPageSize] = useState<number>();
  const [userConfigFetched, setUserConfigFetched] = useState(false);

  const colDefCustomizations = {
    Tags: {
      tooltipValueGetter: (params: any) => params.value,
      cellRenderer: TagCellToolTip,
      cellStyle: {
        display: 'flex',
        justifyContent: "center",
      },
      minWidth:100,
    },
    BPP: {
      cellRenderer: BPPRenderer,
      minWidth:100,
    },
  }

  const getGraphData = async (params: any) => {
    if (params.isExcelExport) {

      const gridAPi = currentGridRef?.current?.api;

      if (!gridAPi) {
        notifyError('Grid is not ready for Excel export!');
        return;
      }

      const isPivot = gridAPi.getPivotMode();
      const isRowGroup = gridAPi.getRowGroupColumns().length > 0;
      const isValue = gridAPi.getValueColumns().length > 0;
      
      if (isPivot || isValue || isRowGroup) {                 
       const exportName = `${FilterPageName.Poogi_OTIF_Analysis}_${moment().format("DD-MM-YYYY")}`;
        gridAPi.exportDataAsExcel({
        fileName: exportName,
        sheetName: exportName
      })
    }
    else {
        const headersdata = currentGridRef?.current?.api.getColumnState();
        const formattedFilters = formatFilterJSON(appliedFilters);
        const body = getBodyForExcelExport({ headersdata, filterData: formattedFilters, colDefMap })
        const response = await getOTIFAnalysisDataExcelExport({ body, report_name: FilterPageName.Poogi_OTIF_Analysis, isExcelExport: 1, graphflag: 0 })
        if (response.status === 200) {
          DownloadExcel(response, FilterPageName.Poogi_OTIF_Analysis)
        } else {
          notifyError('Failed to export Excel file!');
        }
      }
    }
    else {

      try {
        const response = await getOTIFAnalysisData({
          ...params
        });
        setGraphData(response.data.data);
      }
      catch (e) {
        console.log(e);
        notifyError('Failed to fetch Graph data!');
      }
    }
  }

  const getFilterData = async () => {
    try {
      const response = await getPageWiseFilterData({ page_name: FilterPageName.Poogi_OTIF_Analysis });
      setFilterData(response?.data.data);
    } catch (error) {
      console.error(error);
    }
  }
  
  const getUserColumnConfig = async () => {
    try {
      const data = await getUserUIReportConfigData({
        un: user.user.name,
        rn_id: UIGridCode.PoogiOTIFAnalysis
      });

      setUserConfigFetched(true);
      const newConfig = data?.data?.data[0] ? JSON.parse(data?.data?.data[0]?.columns_settings) || [] : [];
      setUserPageSize(newConfig.pageSize ? Number(newConfig.pageSize) : pagination.mtoPageSize);
      setColumnState(newConfig.cs);
        
    } catch (error) {
      console.error(error);
    }
  }

  const setColumnDef = async () => {
    try {
      const response = await getUIConfigData('OTIFAnalysis');
      getColDef(response);
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
                rn_id: UIGridCode.PoogiOTIFAnalysis,
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
                rn_id: UIGridCode.PoogiOTIFAnalysis,
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
                    rn_id: UIGridCode.PoogiOTIFAnalysis,
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

  useEffect(() => {
    setColDef(getColumnDefinations(HeaderData, colDefCustomizations))
  }, [HeaderData])

  useEffect(() => {
    setColumnDef();
    getFilterData();
  }, []);

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

  const ExcelData = () => {
    getGraphData({ isExcelExport: true })
  }
  const themeUi = user?.user?.theme_ui;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {
        (isLoading || isUpdateUserConfig || isGetUserConfig) && <OverlayLoader />
      }
      <MTOActionToolBar
        isGridView={isGridView}
        themeUi={themeUi}
        setIsGridView={setIsGridView}
        isChartGridToggle
        isAddFilterButton
        isExcelExport={isGridView ? true : false}
        onExcelExportClick={ExcelData}
        isFilterOpen={isFilterOpen}
        onAddFilter={onAddFilter}
        toggleFilter={toggleFilter}
        onApplyFilter={onApplyFilter}
        multiFilter={currFilter}
        setMultiFilter={setCurrFilter}
        onFilterRemove={onFilterRemove}
        isMfgSelected={isMfgSelected}
        handleSaveClick={handleSaveClick}
        handleResetClick={handleResetClick}
      />
      <HorizontalViewWrapper style={{ flex: 1 }}>
        {isGridView ? (
          <GridView
          getData={(params:any) => getOTIFAnalysisData({
            ...params
        })}   
            colDef={colDef}
            isLoading={isLoading}
            isError={isError}
            isSuccess={isSuccess}
            setCurrentGridRef={setCurrentGridRef}
            currentGridRef={currentGridRef}
            columnState={columnState}
            appliedFilters={appliedFilters}
            userPageSize={userPageSize}
            setUserPageSize={setUserPageSize}
            userConfigFetched={userConfigFetched}
            handleSaveClick={handleSaveClick}
          />

        ) : (
          <BTRTableWrapper style={{ maxHeight: "95%", paddingLeft: "20px" }}>
            <Allotment vertical={false} separator={false}>
              <Allotment.Pane preferredSize={"50%"}>
                <BTRAllomentSection>
                  <OTIFTrendsGraph graphData={graphData?.otif} />
                </BTRAllomentSection>
              </Allotment.Pane>
              <Allotment.Pane preferredSize={"50%"}>
                <BTRAllomentSection>
                  <OTAndIFTrendsGraph graphData={graphData?.ot_n_if} />
                </BTRAllomentSection>
              </Allotment.Pane>
            </Allotment>
          </BTRTableWrapper>
        )}
      </HorizontalViewWrapper>
    </div>
  );
};
export default OTIFAnalysis;