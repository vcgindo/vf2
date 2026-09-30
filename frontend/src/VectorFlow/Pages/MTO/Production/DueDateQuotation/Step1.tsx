import React, { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { GridOptions, SideBarDef } from 'ag-grid-enterprise';
import _ from 'lodash';
import VFPagination from "../../Common/VFPagination";
import VFTable from '../../Common/VFTable';
import { pagination } from '../../Common/Enum';

interface IStep1Props {
  gridOptions: GridOptions,
  rows: any,
  selectedRows: any,
  currentPageSelectedRows: React.MutableRefObject<any>,
  totalRows: React.MutableRefObject<number>,
  currentPage: number,
  setCurrentPage: React.Dispatch<React.SetStateAction<number>>,
  scheduledOrders: any,
  setSelectedRows: any,
  setCurrentGridRef: any,
  currentGridRef: any,
  columnState: any,
  colDef: any,
  pageCallBack: any,
  setPageCallBack:any,
  savePageSize:any,
  userPageSize:any,
  detailCellRendererParamsConfig?:any
}


const Step1 = forwardRef(({ gridOptions, colDef, rows, selectedRows, currentPageSelectedRows, totalRows, currentPage, setCurrentPage, setSelectedRows, currentGridRef, setCurrentGridRef, columnState, pageCallBack, setPageCallBack, savePageSize,userPageSize,detailCellRendererParamsConfig }: IStep1Props, ref: any) => {

  const [isDisabled, setIsDisabled]= useState<boolean>(true)

  const gridRef = useRef<any>();

  const handlePageChange = useCallback(async (currPage: number) => {
    setCurrentPage(currPage);
  },[]);

  const deselectAllForStep1 = () => {
    gridRef.current?.api.deselectAll();
    setSelectedRows(new Map());
  };

  useImperativeHandle(ref, () => ({
    deselectAllForStep1: deselectAllForStep1
  }));

  const isRowSelectable = useCallback((params: any) => {
    return (params.data.dd == null || params.data.dd == undefined);
  }, []);

  useEffect(()=>{
    if (currentGridRef?.current && columnState?.length) { //&& colDef.length > 0
      const result = currentGridRef?.current?.api.applyColumnState({
        state: columnState,
        applyOrder: true
      });
      if (!result) {
        console.error('Failed to apply column state 1');
      }
    }
  },[columnState]);

  const sideBar = React.useMemo<
  SideBarDef | string | string[] | boolean | null
>(() => {
  return {
    toolPanels: [
      {
        id: "columns",
        labelDefault: "Columns",
        labelKey: "columns",
        iconKey: "columns",
        toolPanel: "agColumnsToolPanel",
        toolPanelParams: {
          suppressPivots: true,
          suppressPivotMode: true,
        },
      },
    ],
  };
}, []);

  return (
    <>
      <VFTable
        key="allRows"
        ref={gridRef}
        gridOptions={gridOptions}
        masterDetail={detailCellRendererParamsConfig.masterDetail}
        detailCellRendererParams={detailCellRendererParamsConfig.detailCellRendererParams}
        columnDefs={colDef}
        rowData={rows}
        isRowSelectable={isRowSelectable}
        rowSelection="multiple"
        onGridReady={(params: any) => {
          params.api.autoSizeAllColumns();
          setCurrentGridRef(gridRef);

          //persist last column state on page call back
          if (pageCallBack) {
            params.api.applyColumnState({
              state: [...columnState],
              applyOrder: true
            });
            setPageCallBack(false);
          }

        }}        
        onRowDataUpdated={(params) => {
          const selectedRowIds = Array.from(selectedRows.keys());
          const newCurrentPageSelected: any = [];
          params.api.forEachNode(node => {
            if (selectedRowIds.includes(node.data.ok)) {
              newCurrentPageSelected.push(node);
            }
          });
          currentPageSelectedRows.current = newCurrentPageSelected;
          params.api.setNodesSelected({ nodes: newCurrentPageSelected, newValue: true });
        }}
        onSelectionChanged={(params: any) => {
          const newMap = new Map(selectedRows);
          const selectedRowIds = Array.from(selectedRows.keys());
          const newCurrentPageSelected: any = [];
          params.api.forEachNode((node:any) => {
            if (selectedRowIds.includes(node.data.ok)) {
              newCurrentPageSelected.push(node);
            }
          });
          currentPageSelectedRows.current = newCurrentPageSelected;
          _.differenceWith(currentPageSelectedRows.current, params.api.getSelectedNodes(), _.isEqual).forEach((node: any) => {
            newMap.delete(node.data.ok);
          });
          params.api.getSelectedNodes().forEach((node: any) => {
            newMap.set(node.data.ok, node);
          });       
          setSelectedRows(newMap);
          currentPageSelectedRows.current = params.api.getSelectedNodes();
        }}
        onFilterChanged={()=>{Object.keys((gridRef?.current?.api?.getFilterModel()))?.length>0 ? setIsDisabled(false) : setIsDisabled(true)}}
        maintainColumnOrder={true}
        sideBar={sideBar}
      />
      <VFPagination
        selectedRows={0}
        totalRows={totalRows.current}
        rowsPerPage={userPageSize || pagination.mtoPageSize}
        currentPage={currentPage}
        handleChangePage={handlePageChange}
        resetGridRef={currentGridRef}
        isDisabled = {isDisabled}
        customPageSizeEnabled={true}
        savePageSize={savePageSize}
        userPageSize = {userPageSize}
      />
    </>
  );
});

export default Step1;
