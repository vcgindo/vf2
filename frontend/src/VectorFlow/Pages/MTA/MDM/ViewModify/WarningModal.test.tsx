import { screen, render } from "@testing-library/react"
import WarningModal from "./WarningModal"
import { UserDataContext } from "../../../../../context"

const mockFunction = jest.fn()

const dummyprops = {
  count:10,
  showAll:true,
  onSuccess:mockFunction,
  onFailure:mockFunction,
  onCloseModal:mockFunction,
  rowsPerPage:20
}

describe("WarningModal Component", () => {
  it("renders the count props in the document ", () => {
    render( <UserDataContext.Provider value={{user:{user:{theme_ui:'NOIRFUSION'}},changeColorTheme:(color) => {return color},isSideBarOpen:true,toggleSideBar:jest.fn}}>
              <WarningModal {...dummyprops} />
            </UserDataContext.Provider>)
    const Modalcount = screen.getByText(10)
    expect(Modalcount).toBeInTheDocument()
   
  })
  
})
