import { screen, render, fireEvent } from "@testing-library/react"
import TaskPendingActionHeader from './TaskPendingActionHeader';

const dummyprops = {
    showApproveAllModal:jest.fn(),
    showRejectAllModal:jest.fn()
}


describe("RejectAllModal Component", () => {
  it("Renders Action Header", () => {
    render(<TaskPendingActionHeader/>)
  })

  it("Approves All Records",()=>{
    render(<TaskPendingActionHeader {...dummyprops}/>);
    const approveAll = screen.getByText("Approve All");
    fireEvent.click(approveAll);

  })

  it("Rejects All Records",()=>{
    render(<TaskPendingActionHeader {...dummyprops}/>);
    const rejectAll = screen.getByText("Reject All");
    fireEvent.click(rejectAll);

  })
    
  
})
