import { useEffect, useMemo, useState } from "react";
import MTOActionToolBar from "../../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar";
import { HorizontalViewWrapper, OrderAtRiskChartWrapper } from "./styles";
import { DownloadExcel, formatFilterJSON, getBodyForExcelExport, getColumnDefinations } from "../../../../../../helpers/utils";
import { reasonColConfig } from "./MockData";
import SplitGraphContainer from "../../../Common/SplitGraphContainer";
import VFInfoToolTip from "../../../../../../components/VectorFLOW/commons/VFInfoToolTip";
import { ProductionInsightsAndTrendsString } from "../../../Common/String";
import { format } from "date-fns";
import { useGetOrderRiskData, useGetOrderRiskDataExcelExport } from "../../../../../Services/MTO/Production/InsightsAndTrends/OrderAtRisk";
import { ReasonOrderAtRiskType } from "../../../../../../../src/types/MTO/types";
import { useGetUIConfigData } from "../../../../../../VectorFlow/Services/MTO/Common/UIConfig";
import OverlayLoader from "../../../Common/Loader";
import { useGetUserUIConfigData, useUpdateUserUIConfigData } from '../../../../../../VectorFlow/Services/MTO/Common/UserUIConfig'
import { ExcelExportName, FilterPageName, UIGridCode } from "../../../Common/Enum";
import { useUserData } from "../../../../../../context/index";
import GridView from "./GridView";
import { useGetFilterData } from '../../../../../../VectorFlow/Services/MTO/Common/CommonFilter';
import useFilter from '../../../../../../hooks/useFilter';
import { notifyError } from "../../../../../../helpers/notify";
import useColDef from "../../../../../../hooks/useColDef";
import BPPRenderer from "../../../Common/BPRRenderer/BPPRenderer";
import { useGetDate } from "../../../../../../VectorFlow/Services/MTO/Production/InsightsAndTrends/RMPMExpediting";

const APIFilterConfig = {
  filSecVisConfig: {
    "Prod_Order_At_Risk" : {
      mjr : true,
      or: true,
      res: true,
      cus: false
    },
  }
};

const OrderAtRisk = () => {
  const [isGridView, setIsGridView] = useState(false);
  const [hideChart1, toggleChart1] = useState(false);
  const [chartLoading, setChartLoading] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [rawData, setRawData] = useState<ReasonOrderAtRiskType[]>([]);
  const [gridData, setGridData] = useState([]);
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
  } = useFilter(filterData, APIFilterConfig.filSecVisConfig.Prod_Order_At_Risk);
  const { mutateAsync: updateUserUIReportConfigData, isLoading: isUpdateUserConfig } = useUpdateUserUIConfigData();
  const { mutateAsync: getUserUIReportConfigData, isLoading: isGetUserConfig } = useGetUserUIConfigData();
  const { mutateAsync: getUIConfigData } = useGetUIConfigData()
  const { user } = useUserData();
  const reportName = "OrdersAtRisk";
  const { mutateAsync: getOrderAtRiskData, isLoading } = useGetOrderRiskData() || {};
  const {colDefMap ,getColDef} = useColDef();
  const { mutateAsync : getOrderAtRiskDataExcelExport} = useGetOrderRiskDataExcelExport();
  const [masterUIConfig, setMasterUIConfig] = useState([]);

  const [userConfigFetched, setUserConfigFetched] = useState<any>(false);
  const [userPageSize, setUserPageSize] = useState<any>();
  const [totalRow, setTotalRow] = useState<number>(0)
  const [currentPage, setCurrentPage] = useState<number>(1)

  const themeUi = user?.user?.theme_ui;

  const { data: apiResponseData } = useGetDate();
 
  const lastRunDate = new Date(apiResponseData?.data?.data).toString() !== "Invalid Date" ? format(new Date(apiResponseData?.data?.data), 'dd MMM yyyy') : '';


  const setColumnDef = async () => {
    try {
      const response = await getUIConfigData(reportName);
      getColDef(response);
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
        rn_id: UIGridCode.ProdOrderAtRisk
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

  const handleSaveClick = async (coldefs?: any,page_size?: any) => {
    try {
      if (coldefs) {
        const fullConfig = { cs: coldefs, pageSize: userPageSize };
        const payload = {
          un: user.user.name,
          rn_id: UIGridCode.ProdStplAndFullKit,
          cs: JSON.stringify(fullConfig),
        };
        await updateUserUIReportConfigData([payload]);
        setColumnState([...coldefs]);

      } 
      else if (page_size) {
        const config = columnState
        const fullConfig = { cs: config, pageSize: page_size };
        const payload = {
          un: user.user.name,
          rn_id: UIGridCode.ProdOrderAtRisk,
          cs: JSON.stringify(fullConfig),
        }
        await updateUserUIReportConfigData([payload]);
      }
      else {
        if (currentGridRef?.current?.api) {
          const config = currentGridRef.current.api.getColumnState();
          const fullConfig = { cs: config, pageSize: userPageSize };
          const payload = {
            un: user.user.name,
            rn_id: UIGridCode.ProdOrderAtRisk,
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

   const savePageSize = (pageSize: any) => {
        if (pageSize) {
          setUserPageSize(pageSize);
          handleSaveClick(false, pageSize);
          } else {
            notifyError("Invalide page size");
        }
        
    }

  const handleResetClick = () => {
    setIsReset(true);
  }

  const getFilterData = async () => {
    try {
        const response = await getPageWiseFilterData({page_name: FilterPageName.Prod_Order_At_Risk });
        setFilterData(response?.data.data);
    } catch (error) {
        console.error(error);
    }
  }

  useEffect(() => {
    setColumnDef();
    getFilterData();
  }, [])


  const colDefCustomizations = {
    BPP: {
      cellRenderer: BPPRenderer,
      minWidth:100
    },
  };

  const gridColDefs = useMemo(() => {
    return getColumnDefinations(reasonColConfig, {}, []);
  }, []);

  const generateHeader = () => {
    return (
      <div
        className="title"
        style={{
          backgroundColor: "white",
          height: "40px",
          display: "flex",
          justifyContent: "right",
          alignItems: "center",
          width: "100%",
        }}
      >
        <div
          data-testid="stpl-graph"
          style={{
            fontSize: "14px",
            margin: "0 auto",

            textAlign: "center",
          }}
        >
          <span style={{ fontWeight: 500 }}>
            {`${ProductionInsightsAndTrendsString.orderAtRisk}  `}
          </span>
          <span style={{ fontWeight: 300 }}>
            {` (${lastRunDate})`}
          </span>
        </div>
        <div style={{ display: "flex" }}>
          <div style={{ marginLeft: 30, marginBottom: "-5px" }}>
            <VFInfoToolTip
              infoList={[
                "The graph highlights the top 10 major and minor reasons for Black/Red open orders.",
              ]}
            />
          </div>
          <div
            data-testid="grid-toggle-btn"
            onClick={() => {
              toggleChart1(!hideChart1);
            }}
            style={{
              marginLeft: 10,
              marginBottom: "-5px",
              marginRight: "10px",
            }}
          >
            <img
              src="/assets/img/VectorFLOW/BPR/minimize.svg"
              height={13}
              width={13}
              color={"#CCCCCC"}
            />
          </div>
        </div>
      </div>
    );
  };

  function TooltipRenderer({ datum }: any) {
    return `
           <div class="ag-chart-tooltip-title" style="background-color: #2E2E2E; display: flex; justify-content: center; color: lightgray;">
              Major Reason
           </div>
           <div class="ag-chart-tooltip-content" style="color: white; background-color: #2E2E2E">
           <div style="border-top: 1px dashed lightgray"></div>
            <div style="display:flex;width: 100%; justify-content: space-between; color: lightgray;">
              <span style="padding: 5px 20px">Total Order</span>
              <span style="padding: 5px 18px">Black</span>
              <span style="padding: 5px 20px">Red</span>
            </div>
            <div style="border-top: 1px dashed lightgray"></div>
            <div style="display:flex ;width: 100%; justify-content: space-around; color: lightgray">
              <span style="padding: 5px ">${(datum?.bo || 0) + (datum?.ro || 0)
      }</span>
              <span style="padding: 5px; margin-left: 30px; ">${datum?.bo || 0
      }</span>
              <span style="padding: 5px ">${datum?.ro || 0}</span>
            </div>
           <div>
            </div>`;
  }

  // const options: AgChartOptions = 

  const [options, setOptions] = useState({});
  
  useEffect(()=>{

   setOptions( {
      data: rawData,
      
      series: [
        {
          type: "bar",
          direction: "horizontal",
          xKey: "r",
          yKey: "bo",
          yName: "Impacted order - Black",
          stacked: true,
          fill: "black",
          tooltip: {
            renderer: TooltipRenderer,
          },
        },
        {
          type: "bar",
          direction: "horizontal",
          xKey: "r",
          yKey: "ro",
          yName: "Impacted order - Red",
          stacked: true,
          fill: "red",
          tooltip: {
            renderer: TooltipRenderer,
          },
        },
      ],
      
      axes: [
        {
          type: "category",
          position: "left",
          title: {
            text: "Major | Minor Reasons",
            fontSize: 10,
            fontWeight: "bold",
          },
          label: {
            fontSize: 8,
            fontWeight: "bold",
            color: "black",
          padding: 10,
        },
        gridLine: {
          enabled: false,
        },
      },
      {
        title: {
          text: "Count Of Orders",
          fontSize: 10,
          fontWeight: "bold",
          spacing: 3,
        },
        type: "number",
        position: "bottom",
        line: { enabled: true },
        label: {
          fontSize: 8,
          fontWeight: "bold",
          color: "black",
        },
        gridLine: {
          enabled: false,
        },
      },
    ],
    
    legend: {
      item: {
        label: {
          fontSize: 10,
        },
      },
    },
  })
  
}, [rawData])
 
      const [isFirstRendered,setIsFirstRendered]=useState(true)
      
      const getData = async (isExcelExport = false,pageSize?:any) => {
        if(isExcelExport) {
            try {

              const gridAPi = currentGridRef?.current?.api;
              if (!gridAPi) {
                notifyError("Grid is not ready for export");
                return;
              }
              const isPivotMode = gridAPi.isPivotMode();
              const isRowGroupingActive = gridAPi.getRowGroupColumns().length > 0;
              const isValueActive =  gridAPi.getValueColumns().length > 0;
               if (isPivotMode || isRowGroupingActive || isValueActive) {                 
                              //  const exportName = `${FilterPageName.Prod_Order_At_Risk}_${moment().format("DD-MM-YYYY")}`;
                               const exportName = ExcelExportName.Order_At_Risk
                               gridAPi.exportDataAsExcel({
                               fileName: exportName,
                               sheetName: exportName
                               });
                }else{ 
                  const headersdata = currentGridRef?.current?.api.getColumnState();
                  const formattedFilters = formatFilterJSON(appliedFilters)
                  const body = getBodyForExcelExport({headersdata, filterData : formattedFilters,colDefMap})
                  const response = await getOrderAtRiskDataExcelExport({body , isExcelExport : 1,report_name : FilterPageName.Prod_Order_At_Risk,page_size: pageSize || userPageSize })
              if(response.status === 200) {
                DownloadExcel(response,FilterPageName.Prod_Order_At_Risk)
              }else{
                notifyError("Failed to export data to Excel")
              }
            }
            } catch (error) {
              notifyError("An error occurred")
              console.log(error)
            }
        }
        else{

          try {
            let payload;
            if(isFirstRendered){
              payload={graphflag:1}
              setIsFirstRendered(false);
            }
            else {
              const formatedFilters= formatFilterJSON(appliedFilters);
              payload = {
                page: currentPage,
                page_size: userPageSize,
                graphflag: 0,
                appliedFilters: formatedFilters
              };
            }
        
            const response = await getOrderAtRiskData(payload);
            if(payload.graphflag==1){
              setRawData(response?.data?.data);
            }
            else{
              setGridData(response.data.data.results || []);
            }
            setTotalRow(response?.data?.data?.count)

          }
          catch (e) {
            console.log(e);
            notifyError('Failed to fetch Grid data!');
          }
        }
  }

  
    useEffect(() => {
      if (Object.entries(appliedFilters).length) {
        getData();    
      }
    }, [currentPage]);


  
    useEffect(() => {
      if (Object.entries(appliedFilters).length && userConfigFetched ) {
        setCurrentPage(1);
    }
    }, [appliedFilters,userConfigFetched])

  
    const handleChangePage = async (currPage: number) => {
      setCurrentPage(currPage);
    }

  useEffect(() => {
    if (isReset) {
      handleSaveClick(masterUIConfig);
      setIsReset(false);
    }
  }, [isReset]);

  useEffect(() => {
    if (currentGridRef?.current && isGridView) {
      setMasterUIConfig(currentGridRef?.current.api.getColumnState());
      getUserColumnConfig();
    }
  }, [colDef, currentGridRef, isGridView]);

  const ExcelExport = () =>{
    getData(true)
  }

  useEffect(()=>{
    getData(false,userPageSize);
  },[userPageSize])

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {(isLoading|| isUpdateUserConfig || isGetUserConfig) && <OverlayLoader />}
      <MTOActionToolBar
        comp={"orderAtRisk"}
        isGridView={isGridView}
        themeUi={themeUi}
        isExcelExport = {isGridView ? true : false} 
        onExcelExportClick={ExcelExport}
        isChartGridToggle
        isAddFilterButton
        setIsGridView={setIsGridView}
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
            gridData={gridData}
            colDef={colDef}
            setCurrentGridRef={setCurrentGridRef}
            currentGridRef={currentGridRef}
            columnState={columnState}
            userPageSize={userPageSize}
            handleChangePage={handleChangePage}
            savePageSize={savePageSize}
            totalRows={totalRow}
            currentPage={currentPage}
            customPageSize={true}
          />
        ) : (
          <OrderAtRiskChartWrapper style={{ maxHeight: "95%", paddingLeft: "20px", paddingBottom:"20px" }}>
            <SplitGraphContainer
              tableLoading={tableLoading}
              chartLoading={chartLoading}
              setTableLoading={setTableLoading}
              setChartLoading={setChartLoading}
              data={rawData}
              rowData={rawData}
              graphTitle={""}
              tableTitle={ProductionInsightsAndTrendsString.orderAtRisk}
              options={options}
              colDef={gridColDefs}
              header={generateHeader}
              hideChart={hideChart1}
              toggleChart={toggleChart1}
              TooltipRenderer={TooltipRenderer}
              graphType={6}
            />
          </OrderAtRiskChartWrapper>
        )}
      </HorizontalViewWrapper>
    </div>
  );
};
export default OrderAtRisk;
