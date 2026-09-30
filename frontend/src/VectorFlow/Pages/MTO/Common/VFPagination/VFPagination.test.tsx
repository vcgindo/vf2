

import { screen, render, fireEvent, cleanup } from "@testing-library/react"
import VFPagination, { VFPaginationProps } from "."

const dummyFn = jest.fn()

const dummyprops:VFPaginationProps = {
    selectedRows:10,
    totalRows:900,
    rowsPerPage:10,
    currentPage:1,
    handleChangePage:dummyFn,
    handleChangePerPage:dummyFn,
    showPagination:true,
    showTotalItems:true
}

describe("VFPagination Component", () => {
  it("renders the component in the document", () => {
    render(<VFPagination {...dummyprops}/>)

    const component = screen.getByTestId('vf_pagination')
    expect(component).toBeInTheDocument()

    cleanup();
    
    
    
  })

  
  it("clicks on the next and previous buttons", () => {
    const customDummy:any =  {
      selectedRows:10,
      totalRows:2,
      rowsPerPage:null,
      currentPage:1,
      handleChangePage:dummyFn,
      handleChangePerPage:dummyFn,
      showPagination:true,
      showTotalItems:true
  }
    render(<VFPagination {...customDummy}/>)

    const nextBtn = screen.getAllByAltText('pagination-next-arrow')
    const previousBtn = screen.getAllByAltText('pagination-prev-arrow')
    const prevLastBtn = screen.getByAltText('pagination-last-prev-arrow')
    const nextLastBtn = screen.getByAltText('pagination-last-next-arrow')

    fireEvent.click(nextBtn[0])
    fireEvent.click(previousBtn[0])
    fireEvent.click(prevLastBtn)
    fireEvent.click(nextLastBtn)
  })

  it("handles edge cases", () => {
    render(<VFPagination {...dummyprops}/>)

    const nextBtn = screen.getByAltText('pagination-next-arrow')
    const previousBtn = screen.getByAltText('pagination-prev-arrow')
    const prevLastBtn = screen.getByAltText('pagination-last-prev-arrow')
    const nextLastBtn = screen.getByAltText('pagination-last-next-arrow')
    fireEvent.click(nextBtn)
    fireEvent.click(previousBtn)
    fireEvent.click(prevLastBtn)
    fireEvent.click(nextLastBtn)
    expect(dummyFn).toBeCalledTimes(2)
  })

  it("handles more edge cases", () => {
    render(<VFPagination {...dummyprops} totalRows={5} rowsPerPage={2000}/>)

    // const nextBtn = screen.getByAltText('pagination-next-arrow')
    // const previousBtn = screen.getByAltText('pagination-prev-arrow')
    // const prevLastBtn = screen.getByAltText('pagination-last-prev-arrow')
    // const nextLastBtn = screen.getByAltText('pagination-last-next-arrow')
    // fireEvent.click(nextBtn)
    // fireEvent.click(previousBtn)
    // fireEvent.click(prevLastBtn)
    // fireEvent.click(nextLastBtn)
    // expect(dummyFn).toBeCalledTimes(2)
  })

  it("handles more more edge cases", () => {
    render(<VFPagination selectedRows={0} handleChangePage={()=>{return}} currentPage={1} totalRows={5} rowsPerPage={10}/>)

    // const nextBtn = screen.getByAltText('pagination-next-arrow')
    // const previousBtn = screen.getByAltText('pagination-prev-arrow')
    // const prevLastBtn = screen.getByAltText('pagination-last-prev-arrow')
    // const nextLastBtn = screen.getByAltText('pagination-last-next-arrow')
    // fireEvent.click(nextBtn)
    // fireEvent.click(previousBtn)
    // fireEvent.click(prevLastBtn)
    // fireEvent.click(nextLastBtn)
    // expect(dummyFn).toBeCalledTimes(2)
    cleanup()
    render(<VFPagination selectedRows={0} handleChangePage={()=>{return}} currentPage={1} totalRows={10} rowsPerPage={10}/>);
  })


})
