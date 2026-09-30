import { screen, render, fireEvent } from "@testing-library/react"
import ApproveModal from "./ApproveModal"
import { UserDataContext } from "../../../../../context"

const mockFunction = jest.fn()

const dummyprops = {
  onSuccess:mockFunction,
  
}

describe("DeleteFileModal Component", () => {
    it("renders the button in the document ", () => {
    render( <UserDataContext.Provider value={{user:{user:{theme_ui:'NOIRFUSION'}},changeColorTheme:(color) => {return color},isSideBarOpen:true,toggleSideBar:jest.fn}}>
                <ApproveModal {...dummyprops} />
            </UserDataContext.Provider>)
        const yesbtn = screen.getByText("Ok")
        expect(yesbtn).toBeInTheDocument()
        fireEvent.click(screen.getByText("Ok"))
    
        const onClose=screen.getByTestId("close-modal-icon")
        expect(onClose).toBeInTheDocument()
        fireEvent.click(screen.getByTestId("close-modal-icon"))
     
  })
  
})
