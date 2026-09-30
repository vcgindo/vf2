import React, { useEffect, useState } from 'react'
import { useGetUIConfigData } from '../../../../../../VectorFlow/Services/MTO/Common/UIConfig';
import MTOActionToolBar from '../../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar'
import ChartView from './ChartView';
import GridView from '../../../Common/GridView';
import { useGetLeadTimeData, useGetLeadTimeExcelData } from '../../../../../../VectorFlow/Services/MTO/Poogi/InsightAndTrends/LeadTime'
import { notifyError, notifySuccess } from '../../../../../../helpers/notify'
import OverlayLoader from '../../../Common/Loader';
import { useUserData } from "../../../../../../context/index";
import { FilterPageName, pagination, UIGridCode } from "../../../Common/Enum";
import { DownloadExcel, formatFilterJSON, getBodyForExcelExport, getColumnDefinations } from '../../../../../../helpers/utils';
import TagCellToolTip from '../../../Poogi/InsightAndTrends/OTIFAnalysis/TagCellRenderer/TagCellRenderer';
import { useGetUserUIConfigData, useUpdateUserUIConfigData } from '../../../../../../VectorFlow/Services/MTO/Common/UserUIConfig'
import useFilter from '../../../../../../hooks/useFilter'
import { useGetFilterData } from '../../../../../../VectorFlow/Services/MTO/Common/CommonFilter'
import useColDef from '../../../../../../hooks/useColDef';
import BPPRenderer from '../../../Common/BPRRenderer/BPPRenderer';
import moment from 'moment';

const APIFilterConfig = {
    filSecVisConfig: {
      "Poogi_Lead_Time" : {
        mjr : false,
        or: false,
        res: true,
        cus: true
      },
    }
};
const LeadTime = () => {
  const [isGridView, setIsGridView] = useState(false);

  const [HeaderData, setHeaderData] = useState();
  const [chartTableData, setChartTableData] = useState([]);
  const [chartData, setChartData] = useState([]);
  const reportName = "LeadTime";
  const [currentGridRef, setCurrentGridRef] = useState<any>(null);
  const [columnState, setColumnState] = useState<any>([]);
  const [colDef, setColDef] = useState([{}]);
  const [isReset, setIsReset] = useState(false);
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
  } = useFilter(filterData, APIFilterConfig.filSecVisConfig.Poogi_Lead_Time);
  const { mutateAsync: updateUserUIReportConfigData, isLoading: isUpdateUserConfig } = useUpdateUserUIConfigData();
  const { mutateAsync: getUserUIReportConfigData, isLoading: isGetUserConfig } = useGetUserUIConfigData();
  const { user } = useUserData();
  const { mutateAsync: getUIConfigData } = useGetUIConfigData();
  const { mutateAsync: getLeadTimeData, isLoading,isError,isSuccess } = useGetLeadTimeData()
  const { colDefMap, getColDef } = useColDef();
  const { mutateAsync: getLeadTimeExcelData } = useGetLeadTimeExcelData();
  const [masterUIConfig, setMasterUIConfig] = useState([]);

  const [userPageSize, setUserPageSize] = useState<number>();
  const [userConfigFetched, setUserConfigFetched] = useState<any>(false);
  
  const setColumnDef = async () => {
    try {
      const response = await getUIConfigData(reportName);
      getColDef(response)
      setHeaderData(response?.data?.data);
    }
    catch (e) {
      console.log(e);
    }
  }

  const getUserColumnConfig = async () => {
    try {
      const data = await getUserUIReportConfigData({
        un: user.user.name,
        rn_id: UIGridCode.PoogiLeadTime
      });
    
      setUserConfigFetched(true);
      const newConfig = data?.data?.data[0]? JSON.parse(data?.data?.data[0]?.columns_settings) || [] :[];
      setUserPageSize(newConfig.pageSize ? Number(newConfig.pageSize) : pagination.mtoPageSize);
      setColumnState(newConfig.cs);
    
      if (!data) {
        console.error('Failed to apply column state');
      }
    } catch (error) {
      console.error(error);
    }
  }
    
  const handleSaveClick = async (coldefs?: any,page_size?:any) => {
    try {
      if (coldefs) {
        const fullConfig = {cs: coldefs, pageSize: userPageSize };
        const payload = {
          un: user.user.name,
          rn_id: UIGridCode.PoogiLeadTime,
          cs: JSON.stringify(fullConfig),
        };
        await updateUserUIReportConfigData([payload]);
        setColumnState([...coldefs]);

      } else if (page_size) {
        const config = columnState;
        const fullConfig = { cs: config, pageSize: page_size };
        const payload = {
          un: user.user.name,
          rn_id: UIGridCode.PoogiLeadTime,
          cs: JSON.stringify(fullConfig),
        };

        await updateUserUIReportConfigData([payload]);

      } else {
        if (currentGridRef?.current?.api) {
          const config = currentGridRef.current.api.getColumnState();
          const fullConfig = { cs: config, pageSize: userPageSize };
    
          const payload = {
            un: user.user.name,
            rn_id: UIGridCode.PoogiLeadTime,
            cs: JSON.stringify(fullConfig)
          }
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
      const response = await getPageWiseFilterData({ page_name: FilterPageName.Poogi_Lead_Time });
      setFilterData(response?.data.data);
    } catch (error) {
      console.error(error);
    }
  }
    
  useEffect(() => {
    setColumnDef();
    getGridData(false);
    getFilterData();
  }, []);  

  const getGridData = async (isExcelExport = false) => {
    if (isExcelExport) {

      const gridApi = currentGridRef?.current?.api;

      if(!gridApi){
        notifyError("Grid API not available for export.");
        return
      }
      
                  const isPivot = gridApi.isPivotMode(); 
                  const isValue = gridApi.getValueColumns().length > 0;
                  const isRowGroup = gridApi.getRowGroupColumns().length > 0;
      
                  if(isPivot || isValue || isRowGroup){
                      const exportName = `${FilterPageName.Poogi_Lead_Time}_${moment().format("DD-MM-YYYY")}`;
                      
                      gridApi.exportDataAsExcel({
                          fileName: exportName,
                          sheetName: exportName
                      })

                    } 

         else {
           const headersdata = currentGridRef?.current?.api?.getColumnState();
           const formatedFilters = formatFilterJSON(appliedFilters)
           const body = getBodyForExcelExport({ headersdata, appliedFilters: formatedFilters, colDefMap })
           try {
             const response = await getLeadTimeExcelData({ body, isExcelExport: 1, report_name: FilterPageName.Poogi_Lead_Time })
             DownloadExcel(response, FilterPageName.Poogi_Lead_Time)
            } catch (error) {
              console.log(error);
            }
          }           
    } else {

      try {
        const data = await getLeadTimeData({ graphflag: 1});
        const chartData: any = []
        const tableData: any = []
        Object.entries(data.data.data).forEach((entry: any) => {
          // console.log(entry1);
          chartData.push({ x: entry[0], y: Object.values(entry[1]).sort((a: any, b: any) => a - b) })
          tableData.push({ ...entry[1], week: entry[0] })
        })
        
        setChartTableData(tableData);
        setChartData(chartData)
        
        notifySuccess("Data Fetched Successfully!");
      }
      catch (err: any) {
        console.log(err)
        notifyError("Something Went Wrong")
      }
    }
  }
    
  const colDefCustomizations = {
    'Tag': {
      tooltipValueGetter: (params: any) => params.value,
      cellRenderer: TagCellToolTip,
      cellStyle: {
        display: 'flex',
        justifyContent: "center",
      },
      minWidth:100,
    },
    'BPP': {
      cellRenderer: BPPRenderer,
      minWidth:100,
    },
  }

  useEffect(() => {
    setColDef(getColumnDefinations(HeaderData, colDefCustomizations))
  }, [HeaderData])

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

  const GetExcelData = () => {
    getGridData(true);
  }
  
  useEffect(() => {
    if (isSuccess) {
      notifySuccess("Fetched Data successfully!")
    }
    if (isError) {
      notifyError("Failed to load data!")
    }
  }, [isSuccess, isError]);

  const themeUi = user?.user?.theme_ui;

    
  return (
    <>
      <MTOActionToolBar
        handleSaveClick={handleSaveClick}
        handleResetClick={handleResetClick}
        handleGoBack={() => { setIsGridView(false) }}
        // isGoBackButton={isGridView}
        themeUi={themeUi}
        isChartGridToggle
        isGridView={isGridView}
        setIsGridView={setIsGridView}
        isExcelExport={isGridView ? true : false}
        onExcelExportClick={GetExcelData}
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
      {(isLoading || isUpdateUserConfig || isGetUserConfig) && <OverlayLoader />}
      {
        isGridView ?
          <>
            <GridView
              getData={(params: any) => getLeadTimeData({
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
          </>
          :
          <>
            <ChartView chartData={chartData} chartTableData={chartTableData} />
          </>
      }
    </>
  )
};

export default LeadTime