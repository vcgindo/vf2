import { screen, render, fireEvent } from "@testing-library/react"
import SubmitConflictModal from "./SubmitConflictModal"
import { UserDataContext } from "../../../../../context"

const mockFunction = jest.fn()

const dummyprops = {
  totalCount:10,
  recordCount:10,
  modificationCount:10,
  errorCount:10,
  onSuccess:mockFunction,
  onFailure:mockFunction,
  onCloseModal:mockFunction
}

describe("SubmitConflictModal Component", () => {
    global.ResizeObserver = class MockedResizeObserver {
        observe = jest.fn();
        unobserve = jest.fn();
        disconnect = jest.fn();
      };
    beforeEach(() => {
        render( <UserDataContext.Provider value={{user:{user:{theme_ui:'NOIRFUSION'}},changeColorTheme:(color) => {return color},isSideBarOpen:true,toggleSideBar:jest.fn}}>
            <SubmitConflictModal {...dummyprops} />
            </UserDataContext.Provider>)
        })
    
        // it("renders the count props in the document ", () => {
        //   screen.debug()
        // const count = screen.getByText(' Are you sure you want to submit 10 records')
        // expect(count).toBeInTheDocument()
        // })
        
        it("renders and fire event on buttons",()=>{
        const yesbtn=screen.getByText("Review")
        const nobtn=screen.getByText("Ignore")
        expect(yesbtn).toBeInTheDocument()
        fireEvent.click(screen.getByText("Review"))
        expect(nobtn).toBeInTheDocument()
        fireEvent.click(screen.getByText("Ignore"))
        })

        // it("renders close icon",()=>{
        //   const onClose=screen.getByTestId("close-modal-icon")
        //   expect(onClose).toBeInTheDocument()
        //   fireEvent.click(screen.getByTestId("close-modal-icon"))
        // })

})

    
       
