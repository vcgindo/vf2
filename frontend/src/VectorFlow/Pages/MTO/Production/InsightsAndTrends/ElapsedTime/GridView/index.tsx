import { GridOptions } from 'ag-grid-enterprise';
import React, { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import VFTable from '../../../../../../../components/VectorFLOW/commons/VFTable'
import CustomTagTooltip from '../../../../Poogi/InsightAndTrends/OTIFAnalysis/CustomTagTooltip';
import './styles.css'
import { SCDynamicContainer } from './styles';
import VFPagination from "../../../../Common/VFPagination";
import { notifyError } from '../../../../../../../helpers/notify';
import { useGetElapsedTimeData } from '../../../../../../../VectorFlow/Services/MTO/Production/InsightsAndTrends/ElapseTime';
import OverlayLoader from '../../../../../../../VectorFlow/Pages/MTO/Common/Loader';
import { pagination } from '../../../../../../../VectorFlow/Pages/MTO/Common/Enum';


const GridView = forwardRef(({ colDef, setCurrentGridRef, currentGridRef, columnState,rowData,userPageSize,handlePageChange,totalRows,currentPage,savePageSize, getGridData,data}: any,ref) => {    
   
    const [isDisabled, setIsDisabled]= useState<boolean>(true)
    const gridRef = useRef<any>(null);
    const {isLoading } = useGetElapsedTimeData()
    

    useImperativeHandle(ref, ()=>({
        getExcelExport: ()=>{
            ExcelExportData();
        }
    }))

    const defaultColDef = {
        // suppressMenu: true,
        autoHeaderHeight: true,
        filter: "agTextColumnFilter",
        floatingFilter: true,
        enableRowGroup: true,
        floatingFilterComponentParams: { suppressFilterButton: true },
        tooltipComponent: CustomTagTooltip,
        initialWidth: 110,
        cellStyle: {
            'text-align': 'center',
            'height': '50px',
            "font-style": "normal",
            "font-variant": "normal",
            "font-size": "12px",
            "font-family": "Roboto",
            'text-overflow': 'ellipsis',
            'white-space': 'nowrap',
            'resizable': 'true',

        },
    }

    const gridOptions: GridOptions = {
        groupDefaultExpanded: 0,
        detailRowHeight: 500,
        rowHeight: 26,
        rowGroupPanelShow: 'always',
        getRowStyle: (params: any) => {
            return {
                background: params.node.rowIndex % 2 === 0 ? "#F4F4F4" : "#FFFFFF",
            };
        },
    };


    useEffect(() => {
        if (currentGridRef?.current && columnState?.length) {
            const result = currentGridRef.current.api.applyColumnState({
                state: columnState,
                applyOrder: true
            });
            if (!result) {
                console.error('Failed to apply column state');
            }
        }
    }, [currentGridRef, columnState]);
    const ExcelExportData = () =>{
        if(data.length> 0){
            
            getGridData(true)
        }
        else{
            notifyError("There is no data that can be exported to Excel!")
        }
    }


    return (

        <SCDynamicContainer className="ag-theme-planning-custom">
            {isLoading && <OverlayLoader />}
            <VFTable
                {...gridOptions}
                sideBar={{
                    toolPanels: ['columns'],
                }}
                columnDefs={colDef}
                defaultColDef={defaultColDef}
                disableZoomScaling
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
                onFilterChanged={()=>{Object.keys((gridRef?.current?.api?.getFilterModel()))?.length>0 ? setIsDisabled(false) : setIsDisabled(true)}}
            // statusBar={{
            //     statusPanels: [
            //         { statusPanel: 'agTotalRowCountComponent', align: 'left' },
            //     ]
            // }}
            />
            <VFPagination
                selectedRows={1}
                totalRows={totalRows}
                currentPage={currentPage}
                rowsPerPage={userPageSize || pagination.mtoPageSize}
                handleChangePage={handlePageChange}
                resetGridRef={currentGridRef}
                isDisabled={isDisabled}
                customPageSizeEnabled={true}
                savePageSize={savePageSize}
                userPageSize = {userPageSize}
            />
        </SCDynamicContainer>

    )
})

export default React.memo(GridView)