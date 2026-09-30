import React, { useEffect, useRef, useState ,useCallback,useMemo} from "react";
import VFTable from "../../../Common/VFTable";
import { GridOptions } from "ag-grid-enterprise";
import OverlayLoader from '../../../Common/Loader';
import { notifyError, notifySuccess } from '../../../../../../helpers/notify';
import { useGetSTPLAndFullKitData } from "../../../../../../VectorFlow/Services/MTO/Production/InsightsAndTrends/STPLAndFullKits";
import { useGetBOMExplosionData } from "../../../../../../VectorFlow/Services/MTO/Common/BOMExplosion";
import VFPagination from "../../../Common/VFPagination";
import { pagination } from "../../../Common/Enum";
import { Wrapper } from "./styles";


const GridView = ({setCurrentGridRef, currentGridRef, columnState, colDef,rowData,userPageSize,handlePageChange,totalRows,currentPage,savePageSize }: any) => {

  const [isDisabled, setIsDisabled]= useState<boolean>(true)
  const { isLoading, isError, isSuccess } = useGetSTPLAndFullKitData();
  const { mutateAsync: getBOMExplosionData, } = useGetBOMExplosionData();


  const gridRef = useRef();

  useEffect(() => {
    if (isSuccess) {
      notifySuccess("Fetched Data successfully!")
    }
    if (isError) {
      notifyError("Failed to load data!")
    }
  }, [isSuccess, isError])

  const getDetailRowData = useCallback(async (params: any) => {
    const data = await getBOMExplosionData({ orderId: params.data.oid, lineId: params.data.lid });
    params.successCallback(data?.data?.data || []);
  }, [getBOMExplosionData]);

  const gridOptions: GridOptions = useMemo(() => ({
    sideBar: {
      toolPanels: [
        {
          id: 'columns',
          labelDefault: 'Columns',
          labelKey: 'columns',
          iconKey: 'columns',
          toolPanel: 'agColumnsToolPanel',
          minWidth: 225,
          maxWidth: 225,
          width: 225,
        },
      ],
    },
    defaultColDef: {
      flex: 1,
      enableRowGroup: true,
    },
    groupDefaultExpanded: 0,
    masterDetail: true,
    detailRowAutoHeight: true,
    detailCellRendererParams: {
      suppressMenu: true,
      detailGridOptions: {
        rowHeight: 30,
        domLayout: 'autoHeight',
        autoGroupColumnDef: {
          headerName: 'Item Name',
          cellRendererParams: {
            suppressCount: true,
          },
        },
        columnDefs: [
          { field: 'qty', headerName: 'Requirement' },
          { field: 'soh', headerName: 'Stock' },
          { field: 'wip', headerName: 'WIP' },
          { field: 'gap', headerName: 'Gap' },
        ],
        defaultColDef: {
          flex: 1,
          suppressMenu: true,
          cellStyle: {
            fontSize: '14px',
            display: 'flex',
            alignItems: 'center',
          },
        },
        treeData: true,
        getDataPath: (data: any) => {
          return data.path;
        },
      },
      getDetailRowData,
    },
  }), [getDetailRowData]);
  

  useEffect(() => {
    if (currentGridRef?.current && columnState?.length && colDef.length > 0) {
      const result = currentGridRef.current.api.applyColumnState({
        state: columnState,
        applyOrder: true
      });
      if (!result) {
        console.error('Failed to apply column state');
      }
    }
  }, [currentGridRef, columnState]);




  return (
    <>
      {
        isLoading && <OverlayLoader />
      }
      <Wrapper data-testid='grid-view'>
        <VFTable
          {...gridOptions}
          columnDefs={colDef}
          rowData={rowData}
          tooltipHideDelay={100000}
          tooltipShowDelay={0}
          tooltipMouseTrack={true}
          ref={gridRef}
          onGridReady={(params: any) => {
            params.api.autoSizeAllColumns();

            setCurrentGridRef(gridRef);
          }}
          maintainColumnOrder
          onFilterChanged={()=>{Object.keys((currentGridRef?.current?.api?.getFilterModel()))?.length>0 ? setIsDisabled(false) : setIsDisabled(true)}}

        />
        <VFPagination
          selectedRows={0}
          rowsPerPage={userPageSize || pagination.mtoPageSize}
          totalRows={totalRows?totalRows:0}
          currentPage={currentPage}
          handleChangePage={(cp)=>handlePageChange(cp)}
          resetGridRef={currentGridRef}
          isDisabled={isDisabled}
          customPageSizeEnabled={true}
          savePageSize={savePageSize}
          userPageSize = {userPageSize}

          />
      </Wrapper>
    </>
  )
}

export default React.memo(GridView);