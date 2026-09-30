import { screen, render } from "@testing-library/react"
import VFModal from "."

const dummyprops = {
  openModal: true,
  closeModal: jest.fn(),
  headerText: "Header",
  headerIcon: '/assets/img/VectorFLOW/NMS/warning.svg',
  children:<p>Hello</p>
}

describe("VFModalCard Component", () => {
  global.ResizeObserver = class MockedResizeObserver {
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
  };
  
  it("renders the component in the document when openModal is true", () => {
    render(<VFModal {...dummyprops}>Hello</VFModal>)
    const headerText = screen.getByText("Header")
    const headerIcon = screen.getByTestId('vfmodal-img')
    expect(headerText).toBeInTheDocument()
    expect(headerIcon).toBeInTheDocument()
    expect(headerIcon).toHaveAttribute('src','/assets/img/VectorFLOW/NMS/warning.svg')
  })

  it("renders the component when closeModal is undefined", () => {
    render(<VFModal {...dummyprops} closeModal={undefined}>Hello</VFModal>)
   
  })
  
})
