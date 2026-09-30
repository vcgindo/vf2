import { screen, render, fireEvent } from "@testing-library/react"
import ApproveAllModal from "./ApproveAllModal"
import { UserDataContext } from "../../../../../context"

const mockFunction = jest.fn()

const dummyprops = {
  onSuccess:mockFunction,
  onClose:mockFunction,
  setSelectionType:mockFunction
}

describe("ApproveAllModal Component", () => {
  it("renders the button and closeIcon in the document ", () => {
    render( <UserDataContext.Provider value={{user:{user:{theme_ui:'NOIRFUSION'}},changeColorTheme:(color) => {return color},isSideBarOpen:true,toggleSideBar:jest.fn}}>
              <ApproveAllModal {...dummyprops} />
            </UserDataContext.Provider>)

            const okbtn=screen.getByText("Ok")
            expect(okbtn).toBeInTheDocument()
            fireEvent.click(screen.getByText("Ok"))

            const onClose = screen.getByTestId("close-modal-icon")
            expect(onClose).toBeInTheDocument()
            fireEvent.click(screen.getByTestId("close-modal-icon")) 
  })
  
})
