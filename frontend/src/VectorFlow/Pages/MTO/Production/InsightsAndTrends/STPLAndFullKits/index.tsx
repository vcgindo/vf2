import { Allotment } from "allotment";
import { useEffect, useState } from "react";
import MTOActionToolBar from "../../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar";
import STPLGraph from "./STPLGraph";
import FullKitGraph from "./FullKitGraph";
import {
  BTRAllomentSection,
  BTRTableWrapper,
  HorizontalViewWrapper,
} from "./styles";
import { useGetSTPLAndFullKitData, useGetSTPLAndFullKitExcelData } from "../../../../../../VectorFlow/Services/MTO/Production/InsightsAndTrends/STPLAndFullKits";
import OverlayLoader from '../../../Common/Loader';
import { notifyError, notifySuccess } from '../../../../../../helpers/notify';
import GridView from "./GridView";
import { useGetUserUIConfigData, useUpdateUserUIConfigData } from '../../../../../../VectorFlow/Services/MTO/Common/UserUIConfig'
import { useGetUIConfigData } from '../../../../../Services/MTO/Common/UIConfig';
import { DownloadExcel, formatFilterJSON, getBodyForExcelExport, getColumnDefinations } from '../../../../../../helpers/utils';
import { FilterPageName, UIGridCode } from "../../../Common/Enum";
import { useUserData } from "../../../../../../context/index";
import { useGetFilterData } from '../../../../../../VectorFlow/Services/MTO/Common/CommonFilter';
import useFilter from '../../../../../../hooks/useFilter';
import useColDef from "../../../../../../hooks/useColDef";
import { format } from "date-fns";
import { useGetDate } from "../../../../../../VectorFlow/Services/MTO/Production/InsightsAndTrends/RMPMExpediting";


const APIFilterConfig = {
  filSecVisConfig: {
    "Prod_STPL_And_FullKits" : {
      mjr : false,
      or: false,
      res: true,
      cus: false
    },
  }
};

const STPLAndFullKits = () => {
  const [isGridView, setIsGridView] = useState(false);
  const { mutateAsync: getSTPLandFullkitInDaysData, isLoading, isError, isSuccess } = useGetSTPLAndFullKitData()
  const [graphData, setGraphData] = useState<any>({});
  const [currentGridRef, setCurrentGridRef] = useState<any>(null);
  const [columnState, setColumnState] = useState<any>([]);
  const [isReset, setIsReset] = useState<any>(undefined);
  const [colDef, setColDef] = useState([{}]);
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
  } = useFilter(filterData, APIFilterConfig.filSecVisConfig.Prod_STPL_And_FullKits);
  const { mutateAsync: updateUserUIReportConfigData, isLoading: isUpdateUserConfig } = useUpdateUserUIConfigData();
  const { mutateAsync: getUserUIReportConfigData, isLoading: isGetUserConfig } = useGetUserUIConfigData();
  const { mutateAsync: getUIConfigData } = useGetUIConfigData();
  
  const reportName = "STPLAndFullKits";
  const { user } = useUserData();
  const { colDefMap,getColDef } = useColDef()
  const { mutateAsync : getSTPLandFullkitInDaysExcelData} = useGetSTPLAndFullKitExcelData();
  const [masterUIConfig, setMasterUIConfig] = useState([]);

  const [userConfigFetched, setUserConfigFetched] = useState<any>(false);
  const [userPageSize, setUserPageSize] = useState<any>();
  const [gridData, setGridData] = useState([]);
  const [totalRow, setTotalRow] = useState<number>(0)
  const [currentPage, setCurrentPage] = useState<number>(1)
  
  const { data: apiResponseData } = useGetDate();
   
  const lastRunDate = new Date(apiResponseData?.data?.data).toString() !== "Invalid Date" ? format(new Date(apiResponseData?.data?.data), 'dd MMM yyyy') : '';

  const themeUi = user?.user?.theme_ui;

  const getGraphData = async (params: any) => {
    const {isExcelExport,graphflag} = params;
    if(isExcelExport) {
      const headersdata = currentGridRef?.current?.api?.getColumnState();
      const formattedFilters = formatFilterJSON(appliedFilters)
      const body = getBodyForExcelExport({headersdata,appliedFilters : formattedFilters,colDefMap})
      try{
          const response = await getSTPLandFullkitInDaysExcelData({body,isExcelExport : 1,graphflag, report_name : FilterPageName.Prod_STPL_And_FullKits})
          DownloadExcel(response, FilterPageName.Prod_STPL_And_FullKits)
      }
      catch(e){
        console.log(e)
      }

    }
    else{

      try {
        const response = await getSTPLandFullkitInDaysData(params);
        setGraphData(response.data.data);
      }
      catch (e) {
        console.log(e);
        notifyError('Failed to fetch Graph data!');
      }
    }
  }

  const getGridData = async (params: any,pageSize?:any) => {
      try {
        const formatedFilters = formatFilterJSON(appliedFilters);
        const response = await getSTPLandFullkitInDaysData({ ...params, appliedFilters: formatedFilters, page_size: pageSize || userPageSize });
        setGridData(response?.data?.data?.results);
        setTotalRow(response?.data?.data?.count)
      }
      catch (e) {
        console.log(e);
        notifyError('Failed to fetch Grid data!');
      }
    }

  const colDefCustomizations = {
    Plant: {
      cellRenderer: "agGroupCellRenderer",
    }
  }


  useEffect(() => {
    if (Object.entries(appliedFilters).length && userConfigFetched) {
      setCurrentPage(1);
      getGridData({ graphflag: 0, page: 1 });
    }
   }, [appliedFilters, userConfigFetched])

  const handlePageChange = async (currPage: number) => {
    setCurrentPage(currPage);
    getGridData({ graphflag: 0, page: currPage });
  }

  

  const savePageSize = (pageSize: any) => {
    if (pageSize) {
      setUserPageSize(pageSize);
        setCurrentPage(1)
        handleSaveClick(undefined, pageSize);
        getGridData({ graphflag: 0, page: 1 }, pageSize);
      } else {
        notifyError("Invalide page size");
    }
    
}

  const setColumnDef = async () => {
    try {
      const response = await getUIConfigData(reportName);
      getColDef(response)
      setColDef(getColumnDefinations(response.data.data, colDefCustomizations, []));
    }
    catch (e) {
      console.log(e);
    }
  }
  
  
  const getUserColumnConfig = async () => {
    try {
      const data = await getUserUIReportConfigData({
        un: user.user.name,
        rn_id: UIGridCode.ProdStplAndFullKit
      });

      setUserConfigFetched(true)
      const newConfig = JSON.parse(data?.data?.data[0]?.columns_settings) || [];
      setUserPageSize(newConfig.pageSize ? Number(newConfig.pageSize) : undefined);
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
        const fullConfig = {cs: coldefs, pageSize: page_size || userPageSize };
        const payload = {
          un: user.user.name,
          rn_id: UIGridCode.ProdStplAndFullKit,
          cs: JSON.stringify(fullConfig),
        };
        await updateUserUIReportConfigData([payload]);
        setColumnState([...coldefs]);

      }
      else if(page_size){
        const config = columnState;
        const fullConfig = { cs: config,  pageSize: page_size};        
        const payload = {
          un: user.user.name,
          rn_id: UIGridCode.ProdStplAndFullKit,
          cs: JSON.stringify(fullConfig),
        };
        await updateUserUIReportConfigData([payload]);
      }
      else {
        if (currentGridRef?.current?.api) {

          const config = currentGridRef.current.api.getColumnState();
          const fullConfig = {  cs: config,  pageSize: userPageSize };
          const payload = {
            un: user.user.name,
            rn_id: UIGridCode.ProdStplAndFullKit,
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
        const response = await getPageWiseFilterData({page_name: FilterPageName.Prod_STPL_And_FullKits});
        setFilterData(response?.data.data);
    } catch (error) {
        console.error(error);
    }
  }

  useEffect(() => {
    setColumnDef();
    getGraphData({ graphflag: 1 });
    getFilterData();
  }, [])

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
    if ((currentGridRef?.current)) {
      setMasterUIConfig(currentGridRef?.current.api.getColumnState());
      getUserColumnConfig();
    }
 
  }, [colDef, currentGridRef, isGridView]);

//   useEffect(() => {
//   if (isGridView && !userConfigFetched) {
//     getUserColumnConfig();
//   }
// }, [isGridView]);

  
  const GetExcelData = async () => {
    getGraphData({graphflag : 0 , isExcelExport : true , appliedFilters})
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {
        (isLoading || isUpdateUserConfig || isGetUserConfig) && <OverlayLoader />
      }
      <MTOActionToolBar
        comp={"stplAndFullKit"}
        isGridView={isGridView}
        setIsGridView={setIsGridView}
        isChartGridToggle
        isAddFilterButton
        themeUi={themeUi}
        isExcelExport={isGridView?true:false}
        onExcelExportClick = {GetExcelData}
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
      <HorizontalViewWrapper style={{ flex: 1 }}>
        {isGridView ? (
          <GridView 
            colDef={colDef}
            setCurrentGridRef={setCurrentGridRef}
            currentGridRef={currentGridRef}
            columnState={columnState}
            appliedFilters={appliedFilters}
            userPageSize={userPageSize}
            handlePageChange={handlePageChange}
            currentPage={currentPage}
            totalRows={totalRow}
            savePageSize={savePageSize}
            rowData={gridData}
          />
        ) : (
          <BTRTableWrapper style={{ height:"95%", paddingLeft: "20px", paddingBottom: "10px" }}>
            <Allotment vertical={false} separator={false}>
              <Allotment.Pane preferredSize={"50%"}>
                <BTRAllomentSection>
                  <STPLGraph graphData={graphData?.stpl} lastRunDate={lastRunDate} />
                </BTRAllomentSection>
              </Allotment.Pane>

              <Allotment.Pane preferredSize={"50%"}>
                <BTRAllomentSection>
                  <FullKitGraph graphData={graphData?.fk} lastRunDate={lastRunDate} />
                </BTRAllomentSection>
              </Allotment.Pane>
            </Allotment>
          </BTRTableWrapper>
        )}
      </HorizontalViewWrapper>
    </div>
  );
};
export default STPLAndFullKits;
