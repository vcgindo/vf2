import React, { useCallback, useEffect, useRef, useState } from "react";
import MTOActionToolBar from "../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar";
import { useUserData } from "../context";
import useColDef from "../hooks/useColDef";
import { pagination } from "../VectorFlow/Pages/MTO/Common/Enum";
import OverlayLoader from "../VectorFlow/Pages/MTO/Common/Loader";
import VFPagination from "../VectorFlow/Pages/MTO/Common/VFPagination";
import VFTable from "../VectorFlow/Pages/MTO/Common/VFTable";
import { useGetUIAndUserConfigData } from "../VectorFlow/Services/MTO/Common/UIConfig";
import { useUpdateUserUIConfigData } from "../VectorFlow/Services/MTO/Common/UserUIConfig";
import { notifyError, notifySuccess } from "./notify";
import {
  DownloadExcel,
  formatFilterJSON,
  getBodyForExcelExport,
  getColumnDefinations,
} from "./utils";

type ExcelExportParams = {
  isExcelExportFromBackend?: boolean;
  excelExportReportName?: string;
  excelExportSheetName?: string;
  showBomExcelModal?: boolean;
};

type columnDefinationPropsType = {
  customColDef?: any;
  extras?: any;
};

export type getExcelExportDataArgs = {
  body: any;
  isExcelExport: number;
  report_name: string;
  isChildren?: number;
};

export type getRowDataArgs = {
  page: number;
  graphflag: number;
  appliedFilters: any;
  page_size?: number;
  isChildren?: number;
};

export type GetGridDataArgs = {
  isExcelExport?: boolean;
  page?: number;
  pageSize?: number;
  isChildren?: number;
};

type actionToolBarPropsType = {
  comp: string;
  isAddFilterButton?: boolean;
  isChartGridToggle?: boolean;
  isExcelExportIcon?: boolean;
  isGridView?: boolean;
  setIsGridView?: (val: boolean) => void;
  isGoBackButton?: boolean;
  handleGoBack?: () => void;
  isFilterOpen?: boolean;
  onAddFilter?: () => void;
  toggleFilter?: (state: boolean) => void;
  onApplyFilter?: (
    filter: any,
    selectedHeader?: any,
    selectedOperator?: any,
    selectedValue?: any
  ) => void;
  isMfgSelected?: boolean;
  multiFilter?: any[];
  setMultiFilter?: (val: any) => void;
  onFilterRemove?: (parentId: string, filterId: any, value: any) => any;
};

type CommonGridviewProps = {
  reportName: string;
  columnDefinationProps: columnDefinationPropsType;
  excelExportParams?: ExcelExportParams;
  customGridOptions?: any;
  setAppliedFilters?: (state: any) => void;
  setCurrentFilters?: (state: any) => void;
  appliedFilters?: any;
  reportNameId?: number;
  getExcelExportData?: (args: getExcelExportDataArgs) => Promise<any>;
  getRowData: (args: getRowDataArgs) => Promise<any>;
  actionToolBarProps: actionToolBarPropsType;
  gridDataLoading: boolean;
  BomExcelExport?: React.FC<{
    onConfirm: () => void;
    onCancel: () => void;
    onClose: () => void;
    showExcelModal: boolean;
  }>;
  VFWrapper: React.ComponentType<{
    children: React.ReactNode;
    className?: string;
    style?: React.CSSProperties;
  }>;
  vfWrapperStyle?: React.CSSProperties;
  vfWrapperClassName?: string;
};

/**
 * CommonGridview
 *
 * A reusable AG Grid wrapper component used to display report data with
 * pagination, filtering, column customization, and Excel export support.
 *
 * Responsibilities:
 * - Renders an AG Grid table with configurable column definitions
 * - Fetches and displays paginated row data using `getRowData`
 * - Applies and persists user-specific grid settings such as:
 *   column width, column order, column visibility, page size, and filters
 * - Allows users to save and reset grid configuration
 * - Supports both frontend and backend driven Excel export
 * - Optionally shows a confirmation modal before Excel export (BOM export)
 *
 * Usage:
 * - Provide column definitions via `columnDefinationProps`
 * - Provide a `getRowData` function to fetch grid data
 * - Optionally provide `getExcelExportData` for backend Excel export
 * - Configure toolbar behavior using `actionToolBarProps`
 *
 * @component
 *
 * @param {CommonGridviewProps} props
 *
 * @param {string} props.reportName
 * Name of the report. Used to fetch UI configuration and for Excel export naming.
 *
 * @param {columnDefinationPropsType} props.columnDefinationProps
 * Contains custom column definitions and additional column options.
 *
 * @param {ExcelExportParams} [props.excelExportParams]
 * Configuration for Excel export behavior, including backend export
 * and optional BOM confirmation modal.
 *
 * @param {any} [props.customGridOptions]
 * Additional AG Grid options passed directly to the grid.
 *
 * @param {(state: any) => void} [props.setAppliedFilters]
 * Callback used to update applied filter state.
 *
 * @param {any} [props.appliedFilters]
 * Object containing currently applied filters used while fetching grid data.
 *
 * @param {number} [props.reportNameId]
 * Unique report identifier used for saving and retrieving user UI configuration.
 *
 * @param {(args: getExcelExportDataArgs) => Promise<any>} [props.getExcelExportData]
 * Function used to fetch Excel data from backend when backend export is enabled.
 *
 * @param {(args: getRowDataArgs) => Promise<any>} props.getRowData
 * Function used to fetch paginated row data for the grid.
 *
 * @param {actionToolBarPropsType} props.actionToolBarProps
 * Configuration object controlling the grid toolbar behavior and actions.
 *
 * @param {boolean} props.gridDataLoading
 * Flag to display loader while grid data is being fetched.
 *
 * @param {React.FC} [props.BomExcelExport]
 * Optional modal component displayed before Excel export
 * when BOM export confirmation is required.
 *
 * @param {React.ComponentType} props.VFWrapper
 * Wrapper component used to style the AG Grid container.
 *
 * @param {React.CSSProperties} [props.vfWrapperStyle]
 * Custom styles applied to the VFWrapper component.
 *
 * @param {string} [props.vfWrapperClassName]
 * Custom class name applied to the VFWrapper component.
 *
 * @returns {JSX.Element}
 * A fully configured grid view with pagination, filtering,
 * column customization, and Excel export support.
 *
 *
 * ------------------------------------------------------------------
 * actionToolBarProps
 * ------------------------------------------------------------------
 *
 * Configuration object used to control the behavior and UI of the grid toolbar
 * rendered by `MTOActionToolBar`.
 *
 * Controls:
 * - Visibility of toolbar buttons (Excel, Save, Reset, Filters, Go Back, Chart toggle)
 * - Filter related actions
 * - Grid view and chart view toggling
 * - Navigation actions like Go Back
 *
 * @param {string} comp
 * Unique identifier for the grid/report.
 *
 * @param {boolean} [isAddFilterButton]
 * Shows or hides the "Add Filter" button.
 *
 * @param {boolean} [isChartGridToggle]
 * Enables toggle between Grid view and Chart view.
 *
 * @param {boolean} [isExcelExportIcon]
 * Shows or hides the Excel export icon in the toolbar.
 *
 * @param {boolean} [isGridView]
 * Indicates current view mode.
 * true  → Grid view
 * false → Chart view
 *
 * @param {(val: boolean) => void} [setIsGridView]
 * Callback to toggle between Grid and Chart views.
 *
 * @param {boolean} [isGoBackButton]
 * Shows or hides the Go Back button.
 *
 * @param {() => void} [handleGoBack]
 * Callback executed when Go Back button is clicked.
 *
 * @param {boolean} [isFilterOpen]
 * Indicates whether the filter panel is currently open.
 *
 * @param {() => void} [onAddFilter]
 * Triggered when the Add Filter button is clicked.
 *
 * @param {(state: boolean) => void} [toggleFilter]
 * Opens or closes the filter panel.
 *
 * @param {(filter: any, selectedHeader?: any, selectedOperator?: any, selectedValue?: any) => void} [onApplyFilter]
 * Called when a filter is applied from the toolbar.
 *
 * @param {boolean} [isMfgSelected]
 * Domain-specific flag used to control toolbar behavior
 * based on Manufacturing or similar selections.
 *
 * @param {any[]} [multiFilter]
 * List of currently applied filters.
 *
 * @param {(val: any) => void} [setMultiFilter]
 * Updates the multi-filter state.
 *
 * @param {(parentId: string, filterId: any, value: any) => any} [onFilterRemove]
 * Called when a filter is removed from the toolbar.
 *
 * @example
 * <CommonGridview
 *   reportName="Sample Report"
 *   columnDefinationProps={{
 *     customColDef: customDefinitions,
 *     extras: additionalOptions,
 *   }}
 *   excelExportParams={{
 *     isExcelExportFromBackend: true,
 *     excelExportReportName: "SampleReport",
 *     showBomExcelModal: true,
 *   }}
 *   getRowData={fetchRowData}
 *   getExcelExportData={fetchExcelData}
 *   actionToolBarProps={toolbarConfig}
 *   gridDataLoading={isLoading}
 *   VFWrapper={SCDynamicContainer}
 *   vfWrapperStyle={ { height: '100%', width: '100%' } }
 *   vfWrapperClassName={exampleClassName}
 * />
 */

function CommonGridview(props: CommonGridviewProps) {
  const {
    appliedFilters,
    reportName,
    columnDefinationProps,
    excelExportParams,
    customGridOptions,
    setAppliedFilters,
    getRowData,
    reportNameId,
    getExcelExportData,
    actionToolBarProps,
    gridDataLoading,
    BomExcelExport,
    setCurrentFilters,
    VFWrapper,
    vfWrapperStyle,
    vfWrapperClassName,
  } = props;

  const {
    mutateAsync: updateUserUIReportConfigData,
    isLoading: isUpdateUserConfig,
  } = useUpdateUserUIConfigData();

  const {
    comp,
    isAddFilterButton = false,
    isExcelExportIcon = true,
    isGoBackButton = false,
    isMfgSelected = false,
    isFilterOpen = false,
    isChartGridToggle = false,
    isGridView,
    multiFilter = [],
    handleGoBack,
    onAddFilter,
    onApplyFilter,
    onFilterRemove,
    setMultiFilter,
    toggleFilter,
    setIsGridView,
  } = actionToolBarProps;

  const { mutateAsync: getUIAndUserConfigData, isLoading: isGetUserConfig } =
    useGetUIAndUserConfigData();

  const { user } = useUserData();
  const [userPageSize, setUserPageSize] = useState<any>();
  const [rowData, setRowData] = useState([]);
  const [totalRow, setTotalRow] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [columnState, setColumnState] = useState<any>([]);
  const [isReset, setIsReset] = useState<any>(undefined);
  const [colDef, setColDef] = useState([{}]);
  const { getNewColDef, colDefMap } = useColDef();
  const [masterUIConfig, setMasterUIConfig] = useState([]);
  const [userConfigFetched, setUserConfigFetched] = useState<any>(false);
  const [isDisabled, setIsDisabled] = useState<boolean>(true);
  const [showExcelModal, setShowExcelModal] = useState<boolean>(false);

  const isPivot = useRef(false);

  const [defaultFilterState, setDefaultFilterState] = useState<any>(appliedFilters || {});

  const gridRef = useRef<any>(null);


  // Set up column definitions
   const setColumnDef = useCallback(async () => {
    try {
      const response = await getUIAndUserConfigData({
        reportName,
        userName: user.user.name,
        reportNameId,
      });
      const defaultColDef = response?.data?.data?.default_coldef;
      const userWiseConfig =
        JSON.parse(response?.data?.data?.columns_settings) || [];

          getNewColDef(response);
          setColDef(
            getColumnDefinations(
              defaultColDef,
              columnDefinationProps?.customColDef,
              columnDefinationProps?.extras
            )
          );
      if (userWiseConfig?.cs && userWiseConfig?.cs?.length > 0) {
        getUserColumnConfig(userWiseConfig);
      }
      setUserConfigFetched(true);
      
    } catch (e) {
      console.log(e);
    }
  },[ reportName, reportNameId, columnDefinationProps, getNewColDef]);

  // Fetch grid data function
  const getGridData = useCallback(async ({
    isExcelExport = false,
    page = 1,
    pageSize,
    isChildren = 0,
  }: GetGridDataArgs) => {
    const formatedFilters = formatFilterJSON(appliedFilters);
    if (isExcelExport && getExcelExportData) {
      try {
        const headersdata = gridRef?.current?.api.getColumnState();
        const body = getBodyForExcelExport({
          headersdata,
          filterData: formatedFilters,
          colDefMap,
        });
        const response = await getExcelExportData({
          body,
          isExcelExport: 1,
          report_name: reportName,
          isChildren,
        });
        if (response.status === 200) {
          DownloadExcel(response, reportName);
          notifySuccess("Data Exported to Excel Successfully!");
        } else {
          notifyError("Failed to Export to Excel");
        }
      } catch (err) {
        console.log(err);
        notifyError("Failed to Export to Excel");
      }
    } else {
     try {
        const data = await getRowData({
          page: page || currentPage,
          graphflag: 0,
          appliedFilters: formatedFilters,
          page_size: pageSize || userPageSize,
        });
        setRowData(data?.data?.data?.results ?? []);
        setTotalRow(data?.data?.data?.count ?? 0);
        notifySuccess("Data Fetched Successfully!");
      } catch (err: any) {
        console.log(err);
        notifyError("Something Went Wrong");
      }
    }
  },[ appliedFilters, getExcelExportData, getRowData, reportName, currentPage, userPageSize, colDefMap]);

  // Apply user column configuration
  const getUserColumnConfig = useCallback((data: any) => {
    if (!data) {
      console.error("Failed to apply column state");
      return;
    }

    const newConfig = data;
    setUserPageSize(
      newConfig.pageSize ? Number(newConfig.pageSize) : undefined
    );
    setColumnState(newConfig.cs);
    isPivot.current = newConfig.pivot;
    if (
      setAppliedFilters &&
      setCurrentFilters &&
      newConfig?.fs?.filters?.length > 0
    ) {
      setAppliedFilters(newConfig.fs);
      setCurrentFilters(newConfig.fs);
    }
  },[ setAppliedFilters, setCurrentFilters]);

  // Handle save click
  const handleSaveClick = useCallback(async (coldefs?: any, page_size?: any) => {
    try {
      let payload: any;
      const currentColumnState = gridRef?.current?.api?.getColumnState();

      // This if block is for saving column definitions when reset is clicked
      if (coldefs) {
        // Apply state immediately to grid
        if (gridRef?.current?.api) {
          gridRef.current.api.applyColumnState({
            state: coldefs,
            applyOrder: true,
          });
          gridRef.current.api.setGridOption("pivotMode", false);
        }
        const fullConfig = {
          pivot: false,
          cs: coldefs,
          pageSize: userPageSize,
          fs: [],
        };
        payload = {
          un: user.user.name,
          rn_id: reportNameId,
          cs: JSON.stringify(fullConfig),
        };
        isPivot.current = false;
      } else if (page_size) {
        const fullConfig = {
          pivot: isPivot.current,
          cs: currentColumnState,
          pageSize: page_size,
          fs: appliedFilters || {},
        };
        payload = {
          un: user.user.name,
          rn_id: reportNameId,
          cs: JSON.stringify(fullConfig),
        };
      } else if (gridRef?.current?.api) {
        const isPivot = gridRef?.current?.api?.isPivotMode();
        const fullConfig = {
          pivot: isPivot,
          cs: currentColumnState,
          pageSize: userPageSize,
          fs: appliedFilters || {},
        };
        payload = {
          un: user.user.name,
          rn_id: reportNameId,
          cs: JSON.stringify(fullConfig),
        };
      }
      await updateUserUIReportConfigData([payload]);
    } catch (error) {
      console.error(error);
    }
  },[ user.user.name, reportNameId, userPageSize, appliedFilters, updateUserUIReportConfigData]);

  // Handle reset click
  const handleResetClick = useCallback(() => {
    setIsReset(true);
  },[]);

  // Handle page change
  const handlePageChange = useCallback(async (currPage: number) => {
    setCurrentPage(currPage);
    getGridData({ page: currPage });
  },[getGridData]);

  // Save page size change
  const savePageSize = useCallback((pageSize: any) => {
    if (pageSize) {
      setUserPageSize(pageSize);
      setCurrentPage(1);
      handleSaveClick(undefined, pageSize);
      getGridData({ pageSize });
    } else {
      notifyError("Invalide page size");
    }
  },[handleSaveClick, getGridData]);
  

  // Cancel export from BOM Excel Export Modal
  const onCancelBomExcelExportModal = useCallback(() => {
    getGridData({ isExcelExport: true });
    setShowExcelModal(false);
  },[getGridData]);

  // Confirm export from BOM Excel Export Modal
  const onConfirmBomExcelExportModal = useCallback(() => {
    getGridData({ isExcelExport: true, isChildren: 1 });
    setShowExcelModal(false);
  },[getGridData]);

  // Fetch grid data on user config fetch or filter change
  useEffect(() => {
    if (userConfigFetched) {
      setCurrentPage(1);
      getGridData({});
    }
  }, [userConfigFetched, appliedFilters, isReset]);


  // Handle reset action
  useEffect(() => {
    if (isReset) {
      if (setAppliedFilters && setCurrentFilters) {
     
        setDefaultFilterState((prevState: any) => {
          if(prevState?.filters) delete prevState.filters
          
          for(const key in prevState){
            prevState[key].filters.forEach((filter:any)=>{
              if(key === "orders"){
                filter.value = [] 
              } else{
                filter.value = ''
              }
            })
          }
          return prevState
        })
        setAppliedFilters(defaultFilterState);
        setCurrentFilters(defaultFilterState);
      }
      handleSaveClick(masterUIConfig);
      setIsReset(false);
    }
  }, [isReset]);

  // Store master UI config on initial load
  useEffect(() => {
    if (gridRef?.current?.api?.getColumnState) {
      setMasterUIConfig(gridRef?.current?.api.getColumnState());
    }
  }, [colDef]);

  // Apply saved column state to grid
  useEffect(() => {
    if (gridRef?.current && columnState?.length) {
      try {
        const result = gridRef.current.api.applyColumnState({
          state: columnState,
          applyOrder: true,
        });

        const applyPivot = gridRef.current?.api.setGridOption(
          "pivotMode",
          isPivot
        );

        if (!result || !applyPivot) {
          throw new Error("Failed to apply column state");
        }
      } catch (error) {
        console.error(error);
      }
    }
  }, [columnState]);


  // Initial column definition setup
  useEffect(() => {
    setColumnDef();
  }, []);

  // Excel export directly from grid
  const excelExportFromGrid = useCallback(() => {
    if (gridRef?.current?.api?.exportDataAsExcel) {
      gridRef.current.api.exportDataAsExcel({
        fileName: `${
          excelExportParams?.excelExportReportName || reportName
        }.xlsx`,
        sheetName: `${excelExportParams?.excelExportSheetName || reportName}`,
      });
    }
  },[ excelExportParams, reportName]);

  // Handle pivot mode changes to show/hide checkbox column
  const onPivotModeChanged = useCallback((event: any) => {
    const isPivotOn = event.api.isPivotMode();
    isPivot.current = isPivotOn;
  },[]);

  // Handle Excel export click
  const onExcelExportClick = useCallback(() => {
    // Excel export from backend if enabled and not in pivot mode and no row groups or value columns
    if (
      excelExportParams?.isExcelExportFromBackend &&
      !isPivot.current &&
      !gridRef?.current?.api?.getRowGroupColumns().length &&
      !gridRef?.current?.api?.getValueColumns().length
    ) {
      if (excelExportParams?.showBomExcelModal) {
        setShowExcelModal(true);
      } else {
        getGridData({ isExcelExport: true, isChildren: 1 });
      }

      // Excel export directly from grid
    } else {
      excelExportFromGrid();
    }
  }, [excelExportParams, getGridData, excelExportFromGrid]);


  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {(isUpdateUserConfig || isGetUserConfig || gridDataLoading) && (
        <OverlayLoader />
      )}
      <MTOActionToolBar
        comp={comp}
        themeUi={user?.user?.theme_ui}
        isAddFilterButton={isAddFilterButton}
        isChartGridToggle={isChartGridToggle}
        isExcelExport={isExcelExportIcon}
        isGridView={isGridView}
        setIsGridView={setIsGridView}
        handleSaveClick={handleSaveClick}
        handleResetClick={handleResetClick}
        onExcelExportClick={onExcelExportClick}
        isFilterOpen={isFilterOpen}
        isGoBackButton={isGoBackButton}
        multiFilter={multiFilter}
        onAddFilter={onAddFilter}
        onApplyFilter={onApplyFilter}
        handleGoBack={handleGoBack}
        onFilterRemove={onFilterRemove}
        setMultiFilter={setMultiFilter}
        isMfgSelected={isMfgSelected}
        toggleFilter={toggleFilter}
        saveBtnName={"Save"}
        resetBtnName={"Reset"}
      />

      <VFWrapper
        className={vfWrapperClassName ?? ".ag-theme-alpine"}
        style={vfWrapperStyle ?? {}}
      >
        <VFTable
          sideBar={{
            toolPanels: ["columns"],
          }}
          columnDefs={colDef}
          disableZoomScaling
          rowData={rowData || []}
          tooltipHideDelay={100000}
          tooltipShowDelay={0}
          pagination={false}
          tooltipMouseTrack={true}
          ref={gridRef}
          maintainColumnOrder={true}
          onColumnPivotModeChanged={onPivotModeChanged}
          onFilterChanged={() => {
            Object.keys(gridRef?.current?.api?.getFilterModel())?.length > 0
              ? setIsDisabled(false)
              : setIsDisabled(true);
          }}
          {...customGridOptions}
        />
        {excelExportParams?.showBomExcelModal && BomExcelExport && (
          <BomExcelExport
            onClose={() => setShowExcelModal(false)}
            onCancel={onCancelBomExcelExportModal}
            onConfirm={onConfirmBomExcelExportModal}
            showExcelModal={showExcelModal}
          />
        )}
        <VFPagination
          selectedRows={0}
          rowsPerPage={userPageSize || pagination.mtoPageSize}
          totalRows={totalRow}
          currentPage={currentPage}
          handleChangePage={handlePageChange}
          resetGridRef={gridRef}
          isDisabled={isDisabled}
          customPageSizeEnabled={true}
          savePageSize={savePageSize}
          userPageSize={userPageSize}
        />
      </VFWrapper>
    </div>
  );
}

export default CommonGridview;
