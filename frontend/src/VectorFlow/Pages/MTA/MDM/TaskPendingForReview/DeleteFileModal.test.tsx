import { screen, render, fireEvent } from "@testing-library/react"
import DeleteFileModal from "./DeleteFileModal"
import { UserDataContext } from "../../../../../context"

const mockFunction = jest.fn()

const dummyprops = {
  onSuccess:mockFunction,
  onFailure:mockFunction,

}

describe("DeleteFileModal Component", () => {
    it("renders the button in the document ", () => {
    render( <UserDataContext.Provider value={{user:{user:{theme_ui:'NOIRFUSION'}},changeColorTheme:(color) => {return color},isSideBarOpen:true,toggleSideBar:jest.fn}}>
                <DeleteFileModal {...dummyprops} />
            </UserDataContext.Provider>)
        const yesbtn = screen.getByText("Yes")
        expect(yesbtn).toBeInTheDocument()
        fireEvent.click(screen.getByText("Yes"))
        const nobtn = screen.getByText("No")
        expect(nobtn).toBeInTheDocument()
        fireEvent.click(screen.getByText("No"))

        const onClose=screen.getByTestId("close-modal-icon")
        expect(onClose).toBeInTheDocument()
        fireEvent.click(screen.getByTestId("close-modal-icon"))
     
  })
  
})
