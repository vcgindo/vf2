import { useRef, useEffect, useState } from "react"
import { pagination } from "../../../../../../../VectorFlow/Pages/MTO/Common/Enum"
import VFTable from "../../../../../../../VectorFlow/Pages/MTO/Common/VFTable"
import { TableWrapper } from "../styles"
import VFPagination from "../../../../Common/VFPagination"

interface GridProps {
    agGridProps: any
    ShortageDatas: any
    setCurrentGridRef: any,
    currentGridRef: any,
    columnState: any,
}

const GridView = ({ agGridProps, colDef, ShortageDatas, setCurrentGridRef, currentGridRef, columnState, orderWiseRecordCount, currentPage, handlePageChangeDayWise, savePageSize, userPageSize }: GridProps | any) => {
    
    const [isDisabled, setIsDisabled] = useState<boolean>(true);
    
    const gridRef = useRef<any>(null);

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
    });


    return (

        <TableWrapper>
            <VFTable
                {...agGridProps}
                columnDefs={colDef}
                rowData={ShortageDatas}
                tooltipHideDelay={100000}
                tooltipShowDelay={0}
                tooltipMouseTrack={true}
                paginationPageSize={pagination.mtoPageSize}
                ref={gridRef}
                pagination={false}
                onGridReady={(params: any) => {
                    params.api.autoSizeAllColumns();

                    setCurrentGridRef(gridRef);
                }}
                maintainColumnOrder
                onFilterChanged={()=>{Object.keys((gridRef?.current?.api?.getFilterModel()))?.length>0 ? setIsDisabled(false) : setIsDisabled(true)}}

            />
            <VFPagination
                selectedRows={0}
                rowsPerPage={userPageSize || pagination.mtoPageSize}
                totalRows={orderWiseRecordCount}
                currentPage={currentPage}
                handleChangePage={handlePageChangeDayWise}
                customPageSizeEnabled={true}
                savePageSize={savePageSize}
                userPageSize={userPageSize}
                isDisabled={isDisabled}
            />
        </TableWrapper>
    )
}

export default GridView