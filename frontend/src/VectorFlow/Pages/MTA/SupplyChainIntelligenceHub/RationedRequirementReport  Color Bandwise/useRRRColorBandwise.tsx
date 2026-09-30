import { useState, useMemo, useEffect, useRef } from "react";
import { AgGridReactProps } from "ag-grid-react";

import { useUserData } from "../../../../../context";
import {
  RRREcoColorCellRenderer,
  RRRDispatchColorCellRenderer,
} from "../RationedRequirementReport/RRRCellRenderers";
import {
  convertUiConfigToOptions,
  getColumnDefinationsMTA,
  CsvExportMTA,
} from "../../../../../helpers/utils";
import { notifyError, notifyLoader, notifySuccess} from "../../../../../helpers/notify"
// import { toast } from "react-toastify";

import useBPRFilter from "../../../../../hooks/useBPRFilter";
import { defaultAgGridSideBarForBPR } from "../../../../../helpers/BPRConstants";
import {
  useGetDailyData,
} from "../../../../Services/MTA/SupplyChainIntelligenceHub/BPR";
import { useGetState } from "../../../../Services/MTA/Common/UserUIConfig";
import { GridRef } from "../../../../types/MDM";
import { ColDef } from "ag-grid-enterprise";

import { TextToTextColorMapper } from "../BPR/BPRCellRenderers";
import { type DailyDataGraph } from "../../../../types/MTA";
import { useDispatch, useSelector } from "react-redux";
import {
  TOGGLE_GRAPH_MODAL,
  UPDATE_DAILY_DATA,
} from "../../../../../redux/actions/MTA";
import BPRGraphCellRenderer from "../BPR/BPRGraphCellRenderer";
import {
  useGetRRRColorBandWiseData,
  useGetRRRColorBandWiseRecordCount,
} from "../../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/RRRColorBandWise";
import { useGetUIConfigData } from "../../../../Services/MTA/Common/UIConfig";
import { UIColumnConfigName, UserUIColumnConfigName } from "../../../../../helpers/Enum";
import { RootState } from "../../../../../redux/store/store";

const useRRRColorBandwise = () => {
  const [internalRef, setInternalRef] = useState<any>();

  const { isSideBarOpen } = useUserData();

  const [RRRColorBandWiseColumns, setRRRColorBandWiseColumns] = useState<
    Array<ColDef>
  >([]);

  const {
    state: currFilter,
    setState: setCurrFilter,
    onDelete,
  } = useBPRFilter();

  const tempRef = useRef();

  const ref = useRef<GridRef>();

  const dispatch = useDispatch();

  const [currentPage, setCurrentPage] = useState<any>(1);

  const [tempDownloadData, setTempDownloadData] = useState<boolean>(false);

  const [exportExcelColumns, setExportExcelColumns] = useState<Array<any>>([]);

  const [exportExcelRowData, setExportExcelRowData] = useState<Array<any>>([]);

  const { mutateAsync: getUiConfig, isLoading: isUIConfigLoading } = useGetUIConfigData();
  

  // const {mutateAsync:getRRRBandwiseData} =useGetRRRData();


  const { mutateAsync: getState, isLoading: isSavedDataLoading } =
    useGetState();

  const [gridState, setGridState] = useState<any>();

  const [recordsCount, setRecordsCount] = useState<number>(0);

  const [rowData, setRowData] = useState([]);

  const { mutateAsync: getDailyData } = useGetDailyData();

  const { mutateAsync: getData , isLoading: isDataLoading} = useGetRRRColorBandWiseData();

  const { mutateAsync: getDataCount , isLoading: isCountDataLoading} = useGetRRRColorBandWiseRecordCount();

  const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
  const RRR_COLORBANDWISE_ROWS_PER_PAGE = EnvConfig['RRR_COLORBANDWISE_ROWS_PER_PAGE']
  const rowsPerPage = parseInt(
    RRR_COLORBANDWISE_ROWS_PER_PAGE || "100"
  );

  const [userPageSize , setUserPageSize]  = useState<number>(RRR_COLORBANDWISE_ROWS_PER_PAGE?parseInt(RRR_COLORBANDWISE_ROWS_PER_PAGE):50)  

  const [initialColumnState, setInitialColumnState] = useState<any>(undefined);
  const [masterUIConfig, setMasterUIConfig] = useState<any>([]);

  // useEffect(() => {
  //   const fetchData = async () => {
  //     await handleGetRecordsCount();
  //     await getRRRColorBandWiseUiConfig();
  //     await loadGridData(currentPage);
  //   };
  //   fetchData();
  // }, []);

  const getRRRColorBandWiseUiConfig = async () => {
    try {
      const response = await getUiConfig(UIColumnConfigName.RRR_OA);
      setInitialColumnState(response.data.data);

    } catch (err: any) {
      notifyError("Something Went Wrong");
    }
  };

  useEffect(() => {
    const getTableState = async () => {
      try {
        const MappedColumns = getColumnDefinationsMTA(initialColumnState,CustomHeader);
              
        setGridState({
          charts: [],
          columns: MappedColumns,
          pivot: false
        })
        setRRRColorBandWiseColumns(MappedColumns);
        getUserColumnConfig();
      } catch (err: any) {
        console.log(err)
            
      }
    }
    if (initialColumnState !== undefined) {
      getTableState()
    }
  }, [initialColumnState]);

  useEffect(() => {
    if (RRRColorBandWiseColumns.length) {
      if (internalRef?.api) {
        setMasterUIConfig(internalRef.api.getColumnState());
      }
    }
  }, [internalRef, RRRColorBandWiseColumns]);
            
  const getUserColumnConfig = async () => {
    const stateData = await getState({ "reportname": UserUIColumnConfigName.RRR_OA })
    if (stateData.data.data.length !== 0) {
      const parsedContent = JSON.parse(stateData.data.data)
                  
      setGridState({
        charts: parsedContent.charts,
        columns: parsedContent.columns,
        pivot: parsedContent.pivot,
      })
            
    } else {
      console.log("Data not available");
    }
  }

  useEffect(() => {
    if (internalRef && gridState && gridState.columns) {
      const result = internalRef.api.applyColumnState({ state: gridState.columns, applyOrder: true });
      internalRef?.api.sizeColumnsToFit();
      if (!result) {
        console.error("Failed to apply column state", result);
      }
    }
  }, [internalRef, gridState]);

  const onResetCallback = async () => {
    setGridState({
      charts: [],
      columns: masterUIConfig,
      pivot: false,
    })
  }

  const handleGetRecordsCount = async (filter?: any) => {
    const payload = {
      filters: filter || currFilter,
      paginationParameter: {
        pageNumber: currentPage,
        // recordPerPage:20
        recordsPerPage: parseInt( RRR_COLORBANDWISE_ROWS_PER_PAGE || "100" ),
      },
    };
    const resultCount = await getDataCount(payload);
    setRecordsCount(resultCount?.data?.data[0]?.count || 0);
  };

    const loadGridData = async (pageNo:any,filter?:any , pageSize?:any)=>{
    const payload = {
      filters: filter || currFilter,
      paginationParameter: { pageNumber: pageNo, recordsPerPage: pageSize || userPageSize || rowsPerPage || 100 },
    };
    const result = await getData(payload);
    setRowData(result?.data.data);
  };

  const onOpenDailyDataGraph = async (params: any) => {
    const payload: any = {
      SKUCode: params.data["SKUCode"],
      WHCode: params.data["WHCode"],
    };
    const result = await getDailyData(payload);
    const data = result.data.data[0];
    const dailyData: DailyDataGraph = {
      rowData: params.data,
      chartData: data["StockData"],
      normChangeData: data["NormChangeHistoryData"],
      masterData: data["MasterData"][0],
      suggestionData: data["SuggestionHistoryData"]
        ? data["SuggestionHistoryData"]
        : [],
      monitoringData: data["MonitoringData"],
    };

    dispatch(UPDATE_DAILY_DATA(dailyData));
    dispatch(TOGGLE_GRAPH_MODAL(true));
  };


  const CustomHeader = {
    dailydatagraph: {
      width: 45,
      minWidth: 45,
      filter: false,
      cellRenderer: 'grapCellRenderer',
      cellRendererParams: { onOpenDailyDataGraph: onOpenDailyDataGraph },
      pinned: 'left',
      resizable: false,
      floatingFilter: false,
      suppressColumnsToolPanel: false,
      suppressMenu:true,
      headerTooltip: "Daily Data Graph",
      headerName:"Daily Data Graph",
      sortable: false,
    },
    DispatchColor: {
      cellRenderer: 'colorCellRenderer',
    },
  }

  const onApplyFilter = async (filter: any) => {
    notifyLoader("Loading Grid Data");
    try {
      await getRRRColorBandWiseUiConfig();
      await handleGetRecordsCount(filter);
      const payload = {
        filters: filter,
        paginationParameter: {
          pageNumber: 1,
          recordsPerPage: userPageSize || rowsPerPage || 100,
        },
      };
      const result = await getData(payload);
      setCurrFilter(filter);
      setCurrentPage(1);
      setRowData(result?.data.data || []); 
      notifySuccess("Data Loaded Successfully");
    } catch (error) {
      console.error(error);
      notifyError("Failed to load data");
    }
  };

  const onDeleteFilter = async (parentId: any, filterId: any, value: any) => {
    const updatedFilter = onDelete(parentId, filterId, value);
    onApplyFilter(updatedFilter);
  };

  const customCellRenderers = useMemo(
    () => ({
      grapCellRenderer: BPRGraphCellRenderer,
      colorCellRenderer: TextToTextColorMapper,
      colorEcoCellRenderer: RRREcoColorCellRenderer,
      colorDispatchRender: RRRDispatchColorCellRenderer,
    }),
    []
  );

  const agGridProps: AgGridReactProps = useMemo(() => {
    return {
      tooltipShowDelay: 0,
      tooltipTrigger: "focus",
      readOnlyEdit: true,
      gridOptions: {
        rowHeight: 50,
        getRowStyle: (params: any) => {
          if (params.node.rowIndex % 2 === 0) {
            return { background: "#EBEBEB" };
          }
          return { background: "#F7F7F7" };
        },
      },
      pagination: false,
      sideBar: defaultAgGridSideBarForBPR,
      // overlayLoadingTemplate:'<object style="position:absolute;top:50%;left:50%;transform:translate(-50%, -50%) scale(2)" type="image/svg+xml" data="/assets/img/VectorFLOW/loaderMedium.svg" aria-label="loading"></object>',
      // rowSelection:'multiple',
      paginationPageSize: parseInt(
        RRR_COLORBANDWISE_ROWS_PER_PAGE || "200"
      ),
      suppressRowClickSelection: true,
      components: customCellRenderers,
      enableBrowserTooltips: true,
      defaultColDef: {
        floatingFilter: true,
        // filter: "agMultiColumnFilter",
        // tooltipComponent:'remarksToolTipComponent',
        cellStyle: {
          "textAlign": "center",
          // "height": "50px",
          // "fontStyle": "normal",
          // "fontVariant": "normal",
          // "fontWeight": "300",
          // "fontSize": "20px",
          // "fontFamily": "Roboto",
          // "display": "block",
          // "textOverflow": "ellipsis",
          // "whiteSpace": "nowrap",
        },
        // ,
        // onCellClicked:(params:any)=>{
        //     console.log(params)
        //     if(params.data.transit && params.data.transit.length>0){
        //         setActiveRow(params.data.transit)
        //         toggleSubGrid(true)
        //         return
        //     }
        //     return setActiveRow(null)
        // }
      },
      onGridReady: (params) => setInternalRef(params),
    };
  }, []);

  const tempAgGridProps: AgGridReactProps = useMemo(() => {
    return {
    onRowDataUpdated: (event) => {
      if (tempDownloadData)
        event.api.exportDataAsExcel({
          fileName: "RationedRequirementReportColorBandwise",
          columnKeys: ref.current?.api
            .getAllDisplayedColumns()
            .map((c) => c.getColId()),
        });
    },
  }
}, [tempDownloadData]);

const onExportToExcelCallBack=async(pageNumber:number)=>{
  const payload = {
      id: 1,
      name: '',
      fields: [],
      filters: currFilter,
      paginationParameter: {
          pageNumber: pageNumber,
          recordsPerPage: 5000
      },
      ISExport:"1",
      reportName:"RRROA",
      stream:1,
      responseType: `arraybuffer`
  }
  notifyLoader("Downloading Data...")
  try {
      await CsvExportMTA(payload, "RRRColorBandwiseReport");
      notifySuccess(`Data Exported Successfully`);
  }
  catch(error) {
      console.log(error);
      notifyError("Error Exporting Excel")
      throw error;
  }
}

  const generalFilterOptions = useMemo(() => {
    return convertUiConfigToOptions(RRRColorBandWiseColumns);
  }, [RRRColorBandWiseColumns]);

  
    const savePageSize = async( pageSize:number)=>{
        setUserPageSize(pageSize)
        await loadGridData(currentPage,currFilter, pageSize);
    }

    const getRRRBandwiseRowData = async (pageNumber: any, pageSize: any) => {
    setCurrentPage(pageNumber);
    await loadGridData(pageNumber, currFilter, pageSize);
  };

  return {
    isSideBarOpen,
    RRRColorBandWiseColumns,
    agGridProps,
    isLoading: isUIConfigLoading || isCountDataLoading || isDataLoading || isSavedDataLoading,
    rowData,
    recordsCount,
    currentPage,
    tempRef,
    tempDownloadData,
    setTempDownloadData,
    tempAgGridProps,
    exportExcelRowData,
    setExportExcelRowData,
    exportExcelColumns,
    setExportExcelColumns,
    onExportToExcelCallBack,
    getRRRBandwiseRowData,
    onApplyFilter,
    currFilter,
    setCurrFilter,
    onDeleteFilter,
    isSavedDataLoading,
    ref,
    generalFilterOptions,
    setCurrentPage,
    onResetCallback,
    savePageSize,
    userPageSize
  };
};

export default useRRRColorBandwise;
