import { UserDataContext } from "../../../../../context/UserDataContext";
import {QueryClientProvider} from '@tanstack/react-query';
import { setupReactQuery } from '../../../../../config/react-query-config';
import { Provider } from 'react-redux';
import { BrowserRouter as Router } from 'react-router-dom'
import { store } from '../../../../../redux/store/store';
import { ReactNode } from 'react';
import UploadModal from "./UploadModal";
import { cleanup, fireEvent, render,screen } from "@testing-library/react";

const queryClient = setupReactQuery()

const contextWrapper = (children:ReactNode) => {
    return(
      <QueryClientProvider client={queryClient}>
          <Router>
            <Provider store={store}>
              <UserDataContext.Provider value={{user:{user:{theme_ui:'NOIRFUSION'}},changeColorTheme:(color) => {return color},isSideBarOpen:true,toggleSideBar:jest.fn}}>
                {children}
              </UserDataContext.Provider>
            </Provider>
          </Router>
        </QueryClientProvider>
    )
  }

const mockFn = jest.fn()

describe('UploadModal',()=>{

  global.ResizeObserver = class MockedResizeObserver {
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
  };


    afterEach(()=>{
      cleanup();
    })
    it('Renders the UploadModal',()=>{
        const file = new File([""], "SKU");
        render(contextWrapper(<UploadModal onCloseModal={mockFn} onDownload={mockFn} onUpload={mockFn} openModal={true} inputText={""} setInputText={jest.fn()} file={file} setFile={jest.fn()} uploadButtonStatus={true}/> ))
    })
    it('Handles File Input When file is not xlsx',()=>{
      const file = new File([""], "SKU.");
      render(contextWrapper(<UploadModal onCloseModal={mockFn} onDownload={mockFn} onUpload={mockFn} openModal={true} inputText={""} setInputText={jest.fn()} file={file} setFile={jest.fn()} uploadButtonStatus={true}/>))

      fireEvent.click(screen.getByTestId('view-modify-manual-upload-btn'));

      fireEvent.change(screen.getByTestId('view-modify-file-upload'), {
        target: { files: [file] },
      })
    })

    it('Handles File Input When file Format is Correct',()=>{
      const file = new File([""], "SKU.xlsx",{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
      render(contextWrapper(<UploadModal onCloseModal={mockFn} onDownload={mockFn} onUpload={mockFn} openModal={true} inputText={""} setInputText={jest.fn()} file={file} setFile={jest.fn()} uploadButtonStatus={true}/>))

      fireEvent.change(screen.getByTestId('view-modify-file-upload'), {
        target: { files: [file] },
      })
    })

    it('Handles File Input When Files Array Length is Empty',()=>{
      const file = new File([""], "SKU.xlsx");
      render(contextWrapper(<UploadModal onCloseModal={mockFn} onDownload={mockFn} onUpload={mockFn} openModal={true} inputText={""} setInputText={jest.fn()} file={file} setFile={jest.fn()} uploadButtonStatus={true}/>))

      fireEvent.change(screen.getByTestId('view-modify-file-upload'), {
        target: { files: [] },
      })
    })

  it('Sets The File Name',()=>{
    const file = new File([""], "SKU");
    render(contextWrapper(<UploadModal onCloseModal={mockFn} onDownload={mockFn} onUpload={mockFn} openModal={true} inputText={""} setInputText={jest.fn()} file={file} setFile={jest.fn()} uploadButtonStatus={true}/>))

    fireEvent.change(screen.getByTestId('view-modify-text'), {target: {value: 'SKU'}})
  })
})