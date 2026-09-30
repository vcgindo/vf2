import { screen, render, fireEvent } from "@testing-library/react"
import SubmitDataModal from "./SubmitDataModal"
import { UserDataContext } from "../../../../../context"

const mockFunction = jest.fn()

const dummyprops = {
  count:10,
  onSuccess:mockFunction,
  onFailure:mockFunction,
  onCloseModal:mockFunction
}

describe("SubmitDataModal Component", () => {
    global.ResizeObserver = class MockedResizeObserver {
        observe = jest.fn();
        unobserve = jest.fn();
        disconnect = jest.fn();
      };
    beforeEach(() => {
        render( <UserDataContext.Provider value={{user:{user:{theme_ui:'NOIRFUSION'}},changeColorTheme:(color) => {return color},isSideBarOpen:true,toggleSideBar:jest.fn}}>
            <SubmitDataModal {...dummyprops} />
            </UserDataContext.Provider>)
        })
    
        // it("renders the count props in the document ", () => {
        //   screen.debug()
        // const count = screen.getByText(' Are you sure you want to submit 10 records')
        // expect(count).toBeInTheDocument()
        // })
        
        it("renders and fire event on buttons",()=>{
        const yesbtn=screen.getByText("Yes")
        const nobtn=screen.getByText("No")
        expect(yesbtn).toBeInTheDocument()
        fireEvent.click(screen.getByText("Yes"))
        expect(nobtn).toBeInTheDocument()
        fireEvent.click(screen.getByText("No"))
        })

        it("renders close icon",()=>{
          const onClose=screen.getByTestId("close-modal-icon")
          expect(onClose).toBeInTheDocument()
          fireEvent.click(screen.getByTestId("close-modal-icon"))
        })

})

    
       
