    import { GridOptions } from 'ag-grid-enterprise';
    import React, { useEffect, useRef, useState } from 'react'
    import VFTable from "../../Common/VFTable";
    import './style.css'
    import { SCDynamicContainer } from './styles';
    import { notifyError, notifySuccess } from '../../../../../helpers/notify';
    import OverlayLoader from '../../../../../VectorFlow/Pages/MTO/Common/Loader';
    import CustomTagTooltip from '../../Poogi/InsightAndTrends/OTIFAnalysis/CustomTagTooltip';
    import VFPagination from "../../Common/VFPagination";
    import { pagination } from '../Enum';
    import { formatFilterJSON } from '../../../../../helpers/utils';

    interface IGridViewProps {
        getData: (isGraph: number) => any,
        colDef: any,
        isLoading: boolean,
        isError: boolean,
        isSuccess: boolean,
        setCurrentGridRef: any,
        currentGridRef: any,
        columnState: any,
        appliedFilters?: any,
        userPageSize?: number,
        setUserPageSize?:any,
        handleSaveClick?: any,
        userConfigFetched?:any
    }

    const GridView = (props: IGridViewProps) => {

        const { getData, isLoading, isError, isSuccess, setCurrentGridRef, currentGridRef, columnState, colDef, appliedFilters, userPageSize, setUserPageSize, handleSaveClick, userConfigFetched } = props;

        const gridRef = useRef<any>(null);
        const [gridData, setGridData] = useState([]);
        const [isDisabled, setIsDisabled]= useState<boolean>(true)
        const [currentPage, setCurrentPage] = useState<number>(1);
        const [totalRows, setTotalRows] = useState<number>(0);
        
        const defaultColDef = {
            autoHeaderHeight: true,
            filter: "agTextColumnFilter",
            floatingFilter: true,
            enableRowGroup: true,
            floatingFilterComponentParams: { suppressFilterButton: true },
            tooltipComponent: CustomTagTooltip,
            initialWidth: 110,
            cellStyle: {
                'text-align': 'left',
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

        const getGridData = async (params: any, page_Size?: any) => {
            try {
                const formatedFilters = formatFilterJSON(appliedFilters);
                const response = await getData({ ...params, appliedFilters: formatedFilters, page_size: page_Size || userPageSize || pagination.mtoPageSize });
                setGridData(response?.data?.data?.results || []);
                setTotalRows(response?.data?.data?.count || 0)
            }
            catch (e) {
                console.log(e);
                notifyError('Failed to fetch Grid data!');
            }
        }

        const handlePageChange = (current: any) => {
            setCurrentPage(current);
            getGridData({ graphflag: 0, page: current})
        }

        useEffect(() => {
            if (Object.keys(appliedFilters).length && userPageSize) {
                getGridData({ graphflag: 0, page: 1 });
                setCurrentPage(1);
            }
        }, [appliedFilters, userConfigFetched]);


        const savePageSize = (pageSize: number) => {
            if (pageSize) {
                setCurrentPage(1);
                setUserPageSize(pageSize);
                handleSaveClick(undefined, pageSize);
                getGridData({ graphflag: 0, page: 1 }, pageSize);
            }
        };

        useEffect(() => {
            if (currentGridRef?.current && columnState?.length) {
                const result = currentGridRef?.current?.api.applyColumnState({
                    state: columnState,
                    applyOrder: true
                });
                if (!result) {
                    console.error('Failed to apply column state');
                }
            }
        }, [columnState, currentGridRef]);

        return (

            <SCDynamicContainer className="ag-theme-planning-custom">
                {
                    isLoading && <OverlayLoader />
                }
                <VFTable
                    {...gridOptions}
                    sideBar={{
                        toolPanels: ['columns'],
                    }}
                    defaultColDef={defaultColDef}
                    columnDefs={colDef}
                    disableZoomScaling
                    rowData={gridData || []}
                    tooltipHideDelay={100000}
                    tooltipShowDelay={0}
                    pagination={false}
                    onGridReady={(params: any) => {
                        params.api.autoSizeAllColumns();
                        setCurrentGridRef(gridRef);
                    }}
                    tooltipMouseTrack={true}
                    ref={gridRef}
                    maintainColumnOrder
                    onFilterChanged={()=>{Object.keys((gridRef?.current?.api?.getFilterModel()))?.length>0 ? setIsDisabled(false) : setIsDisabled(true)}}

                />
                <VFPagination
                    selectedRows={0}
                    rowsPerPage={userPageSize || pagination.mtoPageSize}
                    totalRows={totalRows}
                    currentPage={currentPage}
                    handleChangePage={handlePageChange}
                    resetGridRef={currentGridRef}
                    isDisabled={isDisabled}
                    customPageSizeEnabled ={true}
                    savePageSize={savePageSize}
                    userPageSize={userPageSize}
                />
            </SCDynamicContainer>

        )
    }

    export default React.memo(GridView)