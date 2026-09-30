import { GridOptions } from 'ag-grid-enterprise';
import React, { useEffect, useRef, useState } from 'react'
import VFTable from '../../../../../../../components/VectorFLOW/commons/VFTable'
import CustomTagTooltip from '../../../../Poogi/InsightAndTrends/OTIFAnalysis/CustomTagTooltip';
import './styles.css'
import { SCDynamicContainer } from './styles';
import { useGetLeadTimeData } from '../../../../../../../VectorFlow/Services/MTO/Poogi/InsightAndTrends/LeadTime';
import VFPagination from "../../../../Common/VFPagination";
import { notifyError, notifySuccess } from '../../../../../../../helpers/notify';
import OverlayLoader from '../../../../../../../VectorFlow/Pages/MTO/Common/Loader';
import { pagination } from '../../../../../../../VectorFlow/Pages/MTO/Common/Enum';
import { formatFilterJSON } from '../../../../../../../helpers/utils';

const GridView = ({ colDef, setCurrentGridRef, currentGridRef, columnState, appliedFilters }: any) => {
    const gridRef = useRef(null);

    const [currentPage, setCurrentPage] = useState(1);
    const [totalRows, setTotalRows] = useState(1);
    const [data, setData] = useState([]);
    const [isDisabled, setIsDisabled]= useState<boolean>(true)
    const { mutateAsync: getLeadTimeData, isLoading } = useGetLeadTimeData()

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
            "font-weight": "300",
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

    const getGridData = async () => {
        try {
            const formatedFilters = formatFilterJSON(appliedFilters);
            const data = await getLeadTimeData({ page: currentPage, graphflag: 0, appliedFilters: formatedFilters });
            setData(data?.data?.data?.results)
            setTotalRows(data?.data?.data?.count)
            notifySuccess("Data Fetched Successfully!");
        }
        catch (err: any) {
            console.log(err)
            notifyError("Something Went Wrong")
        }

    }

    useEffect(() => {
        getGridData()
    }, [currentPage, appliedFilters])


    useEffect(()=>{ 
        if (currentGridRef?.current && columnState?.length && colDef.length > 0) {
            const result = currentGridRef.current.api.applyColumnState({
                state: columnState,
                applyOrder: true
            });
            if (!result) {
                console.error('Failed to apply column state');
            }
        }
    });


    const handlePageChange = async (currPage: number) => {
        setCurrentPage(currPage)
    }

    return (

        <SCDynamicContainer className="ag-theme-planning-custom">
            {isLoading && <OverlayLoader />}
            <VFTable
                {...gridOptions}
                sideBar={{
                    toolPanels: ['columns'],
                }}
                defaultColDef={defaultColDef}
                columnDefs={colDef}
                disableZoomScaling
                rowData={data}
                tooltipHideDelay={100000}
                tooltipShowDelay={0}
                tooltipMouseTrack={true}
                ref={gridRef}
                onGridReady={(params: any) => {
                    params.api.autoSizeAllColumns();
                    setCurrentGridRef(gridRef);
                }}
                onFilterChanged={
                    ()=>{Object.keys((currentGridRef?.current?.api?.getFilterModel()))?.length>0 ? setIsDisabled(false) : setIsDisabled(true)}
                }
               
            // statusBar={{
            //     statusPanels: [
            //         { statusPanel: 'agTotalRowCountComponent', align: 'left' },
            //     ]
            // }}
            />
            <VFPagination currentPage={currentPage} totalRows={totalRows} rowsPerPage={pagination.mtoPageSize} selectedRows={1} handleChangePage={handlePageChange} resetGridRef={currentGridRef} isDisabled={isDisabled}
            />
        </SCDynamicContainer>

    )
}

export default React.memo(GridView)