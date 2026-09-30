import useSupplierDispatchReport from "./useSupplierDispatchReport";
import VFTable from "../../../../../components/VectorFLOW/commons/VFTable";
import { GridStateContext } from "../../../../../context/GridStateContext";
import { VDRLayout } from "./styles";
import VFLoader from "../../../../../components/VectorFLOW/commons/VFLoader";
import VFPagination from "../../../../../VectorFlow/Pages/MTO/Common/VFPagination"
import ActionToolBar from "../Planning/ActionToolBar";
import { useState } from "react";
import { useSelector } from "react-redux";
import { RootState } from "../../../../../redux/store/store";


const SupplierDispatchReport = () => {
  

  const {
    VDRColumns,
    RowData,
    SDRCount,
    currentPage,
    setExportExcelColumns,
    exportExcelColumns,
    tempDownloadData,
    setTempDownloadData,
    exportExcelRowData,
    setExportExcelRowData,
    isLoading,
    GetSDRData,
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
  savePageSize,
  userPageSize
  } = useSupplierDispatchReport();

      const [isDisabled, setIsDisabled]= useState<boolean>(true)
  
   
      const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
      const SUPPLIER_DISPATCH_REPORT_PER_PAGE = EnvConfig['SUPPLIER_DISPATCH_REPORT_PER_PAGE'];   

  
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
        onResetCallback:onResetCallback
      }}
    >
      <div style={{marginLeft:'10px'}}>
      <ActionToolBar 
        view={'grid'} 
        setCurrentTab={''} 
        currCategory={'SDR'} 
        currentTab={''} 
        tabsList={[]} 
        onApplyFilter={(e)=>onApplyFilter(e)}
        onFloatingTabChange={()=>console.log('')} 
        onGoBack={()=>console.log('')} 
        onViewChange={()=>console.log('')}
        genericRecordCount={SDRCount}
        onExportToExcelCallBack={onExportToExcelCallBack}
        multiFilter={currFilter}
        generalFilterOptions={generalFilterOptions}
        setMultiFilter={setCurrFilter}
        onDelete={onDeleteFilter}
      />
      </div>
      <VDRLayout>
      {(isLoading )?(
          <VFLoader/>
        ):
      (<div style={{height:'70vh'}}>
       <VFTable
                  ref={ref}
                  {...agGridProps}
                  columnDefs={VDRColumns}
                  rowData={RowData}
                  height={'100%'}
                  onFilterChanged={() => {
                    const filterModel = ref?.current?.api?.getFilterModel();
                    if (filterModel && Object.keys(filterModel).length > 0) {
                      setIsDisabled(false);
                    } else {
                      setIsDisabled(true);
                    }
                }}
                  maintainColumnOrder
        />
        <div>
          {
              RowData?.length  > 0 &&
        <VFPagination 
                selectedRows={0} 
                totalRows={SDRCount} 
                currentPage={currentPage} 
                rowsPerPage={userPageSize}
                handleChangePage={(e)=>GetSDRData(e)} 
                resetGridRef={ref} 
                isDisabled={isDisabled}
                customPageSizeEnabled={true}
              userPageSize={userPageSize}
              savePageSize={savePageSize}
              />
               }
            </div>
        </div>
      )}
      <div style={{display:'none'}}>                
          <VFTable
            ref={tempRef}
            columnDefs={VDRColumns}
            rowData={exportExcelRowData}
            {...tempAgGridProps}
          />
        </div>
      </VDRLayout>
    </GridStateContext.Provider>
  );
};

export default SupplierDispatchReport;
