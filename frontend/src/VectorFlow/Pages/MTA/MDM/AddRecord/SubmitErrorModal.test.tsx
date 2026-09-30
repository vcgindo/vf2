import {  render } from "@testing-library/react"
import SubmitErrorModal from "./SubmitErrorModal"
import { UserDataContext } from "../../../../../context"

const mockFunction = jest.fn()

const dummyprops = {
  totalCount:10,
  recordCount:10,
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
    it("renders the component",()=>{
        render( <UserDataContext.Provider value={{user:{user:{theme_ui:'NOIRFUSION'}},changeColorTheme:(color) => {return color},isSideBarOpen:true,toggleSideBar:jest.fn}}>
            <SubmitErrorModal {...dummyprops} />
            </UserDataContext.Provider>)
    })
})

    
       
