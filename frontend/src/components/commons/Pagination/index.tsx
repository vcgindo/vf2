import ReactPaginate from 'react-paginate'
import './styles.css'
import { useTranslation } from 'react-i18next'
export interface PaginationProps {
  page: any
  handleChangePage: (page: number) => void
  handleChangePerPage?: (page: number) => void
  pageCount: number
}

const Pagination = ({
  page,
  pageCount,
  handleChangePage
}: PaginationProps) => {
  const { t } = useTranslation()

  const handlePageClick = (e: any) => {
    handleChangePage(e.selected + 1)
  }

  return (
    <>
      <ReactPaginate
        className="paginate"
        nextLabel={t('pagination.next')}
        forcePage={page - 1}
        onPageChange={handlePageClick}
        pageRangeDisplayed={pageCount < 4 ? pageCount : 4}
        marginPagesDisplayed={2}
        pageCount={pageCount}
        previousLabel={t('pagination.previous')}
        previousClassName={page == 1 ? "disabledBtn": ""}
        nextClassName={page == pageCount ? "disabledBtn": ""}
        renderOnZeroPageCount={null}
      />
    </>
  )
}

export default Pagination