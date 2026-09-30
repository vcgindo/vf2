import useElephantOrders from "./useElephantOrders";
import VFTable from "../../../../../components/VectorFLOW/commons/VFTable";
import { GridStateContext } from "../../../../../context/GridStateContext";
import { EOLayout } from "./styles";
import VFPagination from "../../../../../VectorFlow/Pages/MTO/Common/VFPagination";
import ActionToolBar from "../Planning/ActionToolBar";
import { useState } from "react";
import VFSave from "./VFSave";
import OverlayLoader from "../../../../../VectorFlow/Pages/MTO/Common/Loader";
import { useSelector } from "react-redux";
import { RootState } from "../../../../../redux/store/store";

const ElephantOrder = () => {
  const {
    isSavedDataLoading,
    VDRColumns,
    RowData,
    EOCount,
    currentPage,
    setExportExcelColumns,
    exportExcelColumns,
    tempDownloadData,
    setTempDownloadData,
    exportExcelRowData,
    setExportExcelRowData,
    isLoading,
    GetEOData,
    tempRef,
    tempAgGridProps,
    currFilter,
    setCurrFilter,
    onDeleteFilter,
    onExportToExcelCallBack,
    onApplyFilter,
    ref,
    agGridProps,
    generalFilterOptions,
    onResetCallback,
    onSubmitDueDate,
     savePageSize,
        userPageSize
  } = useElephantOrders();

      const [isDisabled, setIsDisabled]= useState<boolean>(true)
  
      const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
      const ELEPHANT_ORDER_ROWS_PER_PAGE = EnvConfig['ELEPHANT_ORDER_ROWS_PER_PAGE'];   

  return (
    <GridStateContext.Provider
      value={{
        ref: ref,
        exportExcelColumns: exportExcelColumns,
        setExportExcelColumns: setExportExcelColumns,
        tempDownloadData: tempDownloadData,
        setTempDownloadData: setTempDownloadData,
        exportExcelRowData: exportExcelRowData,
        setExportExcelRowData: setExportExcelRowData,
        onResetCallback: onResetCallback,
      }}
    >
      <div style={{ marginLeft: "10px" }}>
        <ActionToolBar
          view={"grid"}
          setCurrentTab={""}
          currCategory={"EO"}
          currentTab={""}
          tabsList={[]}
          onApplyFilter={(e) => onApplyFilter(e)}
          onFloatingTabChange={() => console.log("")}
          onGoBack={() => console.log("")}
          onViewChange={() => console.log("")}
          genericRecordCount={EOCount}
          onExportToExcelCallBack={onExportToExcelCallBack}
          multiFilter={currFilter}
          generalFilterOptions={generalFilterOptions}
          setMultiFilter={setCurrFilter}
          onDelete={onDeleteFilter}
        />
      </div>
      <EOLayout>
        {(isLoading || isSavedDataLoading) && <OverlayLoader />}
        <div style={{ height: "60vh" }}>
          <VFTable
            ref={ref}
            {...agGridProps}
            columnDefs={VDRColumns}
            rowData={RowData}
            statusBar={{
              statusPanels: [
                {
                  statusPanel: "agTotalAndFilteredRowCountComponent",
                  align: "left",
                },
                { statusPanel: "agTotalRowCountComponent", align: "left" },
                { statusPanel: "agFilteredRowCountComponent", align: "left" },
                { statusPanel: "agSelectedRowCountComponent", align: "left" },
                { statusPanel: "agAggregationComponent", align: "left" },
              ],
            }}
            height={"100%"}
            maintainColumnOrder={true}
            onFilterChanged={() => {
              const filterModel = ref?.current?.api?.getFilterModel();
              if (filterModel && Object.keys(filterModel).length > 0) {
                setIsDisabled(false);
              } else {
                setIsDisabled(true);
              }
            }}
          />

          <div>
            {
              RowData?.length  > 0 &&
            <VFPagination
              selectedRows={0}
              totalRows={EOCount}
              currentPage={currentPage}
              rowsPerPage={userPageSize || parseInt(
                ELEPHANT_ORDER_ROWS_PER_PAGE || "100"
              )}
              handleChangePage={(e) => GetEOData(e)}
              resetGridRef={ref}
              isDisabled={isDisabled}
              customPageSizeEnabled={true}
              userPageSize={userPageSize}
              savePageSize={savePageSize}  
            />
        }
            <VFSave onSubmitDueDate={onSubmitDueDate} />
          </div>
        </div>
        <div style={{ display: "none" }}>
          <VFTable
            ref={tempRef}
            columnDefs={VDRColumns}
            rowData={exportExcelRowData}
            {...tempAgGridProps}
          />
        </div>
      </EOLayout>
    </GridStateContext.Provider>
  );
};

export default ElephantOrder;
