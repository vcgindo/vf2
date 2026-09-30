
import { GridFilterWrapper, TextBtn } from "../../../../VectorFlow/Pages/MTO/Common/VFPagination/styles"
import { PaginationWrapper,StatusBarLabel,StatusBarLabelLight,StatusBarLabelBold,PaginationContainer, PaginationArrowIcon } from "./styles"
import { CSSProperties } from 'react'
import { useUserData } from '../../../../context';




export interface VFPaginationProps{
    selectedRows:number
    totalRows:number
    currentPage:number
    rowsPerPage:number
    handleChangePage:(e:any)=>void
    handleChangePerPage?:(e:any)=>void
    showTotalItems?:boolean,
    showPagination?:boolean,
    style?:CSSProperties,
    resetGridRef?: any,
    isDisabled?:any,
    isClearGridFilter?:boolean,
    customPageSizeEnabled?:any,
    userPageSize?:number,
    savePageSize?:(pageSize:number)=>void
    
}


const VFPagination  = (props:VFPaginationProps)=>{

    const{
        totalRows,
        currentPage,
        rowsPerPage,
        style,
        handleChangePage,
        resetGridRef,
        isDisabled,
        isClearGridFilter = true
    } = props


    const { user } = useUserData();
    const themeUi = user?.user?.theme_ui;
    const defaultPaginationLimit = 100;
    const totalPages = Math.max(Math.ceil(totalRows / (props.rowsPerPage || defaultPaginationLimit)),1)

   // const totalPages = Math.ceil(totalRows/rowsPerPage)
    
    const getTotalItemsString = () => {
        if(totalRows===0) return `0 to ${totalRows}`
        if(totalRows <= rowsPerPage) return `1 to ${totalRows}`;        
        if(currentPage===1) return `1 to ${rowsPerPage}`;
        const start = (currentPage * rowsPerPage)-rowsPerPage + 1;
        const end = (currentPage)*rowsPerPage;
        // console.debug(end,totalRows)
        if(end >= totalRows) return `${start} to ${totalRows}`;
        return `${start} to ${(currentPage)*rowsPerPage}`;
    }

    const handleOnClick = (newPage:number)=>{
        if(newPage===currentPage)return 
        if(newPage >totalPages)return 
        if(newPage<1)return 
        return handleChangePage(newPage)
    }

    const clearGridFilter = () => {
        if (resetGridRef?.current?.api) {
            resetGridRef.current.api.setFilterModel(null);
            resetGridRef.current.api.onFilterChanged(); 
        }
    };


    return (
      <PaginationWrapper data-testid="vf_pagination" style={style}>
        <PaginationContainer>
          {isClearGridFilter && (
            <GridFilterWrapper>
              <TextBtn
                onClick={clearGridFilter}
                disabled={isDisabled}
                themeUi={themeUi}
              >
                Clear All Grid Filters
              </TextBtn>
            </GridFilterWrapper>
          )}
          <StatusBarLabel>
            <StatusBarLabelBold>{getTotalItemsString()}</StatusBarLabelBold>
            <StatusBarLabelLight>of</StatusBarLabelLight>
            <StatusBarLabelBold>{totalRows}</StatusBarLabelBold>
          </StatusBarLabel>
          <StatusBarLabel style={{ marginLeft: "10px" }}>
            <PaginationArrowIcon
              disabled={currentPage === 1}
              src="/assets/img/VectorFLOW/NMS/pagination-last-arrow.svg"
              style={{ transform: "rotate(180deg)" }}
              onClick={() => handleOnClick(1)}
              alt="pagination-last-prev-arrow"
            />
            <PaginationArrowIcon
              disabled={currentPage === 1}
              src="/assets/img/VectorFLOW/NMS/pagination-arrow.svg"
              style={{ transform: "rotate(180deg)" }}
              onClick={() => handleOnClick(currentPage - 1)}
              alt="pagination-prev-arrow"
            />
            <StatusBarLabelLight>Page</StatusBarLabelLight>
            <StatusBarLabelBold>{currentPage}</StatusBarLabelBold>
            <StatusBarLabelLight>of</StatusBarLabelLight>
            <StatusBarLabelBold>{totalPages}</StatusBarLabelBold>

            <PaginationArrowIcon
              disabled={currentPage === totalPages}
              src="/assets/img/VectorFLOW/NMS/pagination-arrow.svg"
              onClick={() => handleOnClick(currentPage + 1)}
              alt="pagination-next-arrow"
            />
            <PaginationArrowIcon
              disabled={currentPage === totalPages}
              src="/assets/img/VectorFLOW/NMS/pagination-last-arrow.svg"
              onClick={() => handleOnClick(totalPages)}
              alt="pagination-last-next-arrow"
            />
          </StatusBarLabel>
        </PaginationContainer>
      </PaginationWrapper>
    );
}

export default VFPagination