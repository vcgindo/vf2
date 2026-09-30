import { VFWrapper } from './styles';
import { SaveBtnWrapper, SaveBtn } from '../../Poogi/ReasonOrderChange/styles';
import VFPagination from "../../Common/VFPagination";
// import { pagination } from '../../Common/Enum';
// import VFTable from '../../../../../components/VectorFLOW/commons/VFTable';
import VFTable from '../../Common/VFTable';
import { memo, useState } from 'react';
import { useUserData } from '../../../../../context';
import { pagination } from '../../Common/Enum';
interface GridProps {
    agGridProps: any
    columDef: any
    convercolumnDef: any
    reference?: any
    updateReason?: () => void
    handlePageChange: (e: any) => any
    totalRow?: any
    currentPage?: any,
    saveBtn?: boolean,
    onGridReady?: any
    excelStyles?: any,
    customPageSize?:boolean,
    savePageSize?: (e: any) => void,
    userPageSize?:any,
    detailCellRendererParamsConfig?:any

}

const GridView = memo(({
    agGridProps,
    columDef,
    convercolumnDef,
    reference,
    updateReason,
    handlePageChange,
    totalRow,
    currentPage,
    onGridReady,
    excelStyles,
    saveBtn = true,
    customPageSize=false,
    userPageSize,
    detailCellRendererParamsConfig,
    savePageSize}: GridProps) => {

    const rowsPerPage = userPageSize || Number(process.env.REACT_APP_MTO_BM_REPORT_ROWS_PER_PAGE) || pagination.mtoPageSize;


    const { user } = useUserData();
    const themeUi = user?.user?.theme_ui;
        
    const [isDisabled, setIsDisabled]= useState<boolean>(true);
     const canAddComments = user.feature_permission.includes("Add_Comments");


    return (
        <>
            <VFWrapper className="wrapper-overall">
                <VFTable
                    {...agGridProps}
                    maintainColumnOrder
                    pagination={false}
                    columnDefs={columDef}
                    excelStyles={excelStyles}
                    rowData={convercolumnDef}
                    tooltipHideDelay={100000}
                    tooltipShowDelay={0}
                    //detailRowHeight={400}
                    rowSelection={'multiple'}
                    detailRowAutoHeight
                    tooltipMouseTrack={true}
                    masterDetail={detailCellRendererParamsConfig?.masterDetail}
                    detailCellRendererParams={detailCellRendererParamsConfig?.detailCellRendererParams}
                    //defaultColDef={{maxWidth:150}}
                    onGridReady = {()=>{
                        if(onGridReady){
                            onGridReady();
                        }
                    }}
                    ref={reference}
                    onFilterChanged={()=>{Object.keys((reference?.current?.api?.getFilterModel()))?.length>0 ? setIsDisabled(false) : setIsDisabled(true)}}
                />
            <VFPagination
                selectedRows={0}
                rowsPerPage={rowsPerPage?rowsPerPage: 0}
                totalRows={totalRow?totalRow: 0}
                currentPage={currentPage?currentPage: 0}
                handleChangePage={handlePageChange}
                resetGridRef={reference}
                isDisabled = {isDisabled}
                customPageSizeEnabled={customPageSize}
                savePageSize={savePageSize}
                userPageSize={userPageSize}
            />
            </VFWrapper>
            {
                saveBtn && canAddComments && (
                    <SaveBtnWrapper style={{ margin: '1rem 0', padding: 0, cursor: 'pointer' }}>
                        <SaveBtn onClick={updateReason} theme={themeUi}>
                            Save Remark
                        </SaveBtn>
                    </SaveBtnWrapper>
                )
            }
        </>
    )
})

export default GridView