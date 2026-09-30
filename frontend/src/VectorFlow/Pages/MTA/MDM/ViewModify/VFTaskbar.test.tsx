import { render, screen } from "@testing-library/react"
import { UserDataContext } from "../../../../../context"
import VFTaskBar from "./VFTaskbar"

const mockFn = jest.fn()
const dummyProps = {
    onBack:mockFn,
    onBack1:mockFn,
    onClearAndExportErrors:mockFn,
    onModifyData:mockFn,
    onReset:mockFn,
    onSubmit:mockFn,
    onDeleteSelected:mockFn,
    onExportData:mockFn,
    onEditOnline:mockFn,
    onSaveToDraft:mockFn,
    onEditOnlineSave:mockFn,
    onSeasonalityStop:mockFn,
    onSeasonalityResume:mockFn,
    onPhaseInPhaseOutStop:mockFn,
    onDeleteOnlone:mockFn,
    onDeleteOnline:mockFn,
    onDeleteOnlineSubmit:mockFn,
    onDeleteData:mockFn,
    onDeleteOnlineReset:mockFn,
    onDeleteOnlineSave:mockFn,
    onSubmitConflictData:mockFn,
    disableResumeSeasonality:mockFn,
    disableStopSeasonality:mockFn,
    enableEditOnlineReset:false,
    showSubmittedExportError:true,
    masterId:1,
    isSavingToDraft:false
}

const contextWrapper = (children:any)=>{
    return (
        <UserDataContext.Provider
            value={{
              user: { user: { theme_ui: "NOIRFUSION" } },
              changeColorTheme: (color) => {
                return color;
              },
              isSideBarOpen:true,toggleSideBar:jest.fn
            }}
          >
            {children}
          </UserDataContext.Provider>
    )
}

describe("VFTaskBar",()=>{
    it('renders the VFTaskBar',()=>{
        render(contextWrapper(<VFTaskBar {...dummyProps} masterProgress="submitted"/>))
        const taskbar = screen.getByTestId("taskbar")
        expect(taskbar).toBeInTheDocument()
    })
    it('renders the VFTaskBar with masterProgress=view',()=>{
        render(contextWrapper(<VFTaskBar {...dummyProps} masterProgress="view"/>))
        const taskbar = screen.getByTestId("taskbar")
        expect(taskbar).toBeInTheDocument()
    })
    it('renders the VFTaskBar with masterProgress=default',()=>{
        render(contextWrapper(<VFTaskBar {...dummyProps} masterProgress="default"/>))
    })
    it('renders the VFTaskBar with masterProgress=error',()=>{
        render(contextWrapper(<VFTaskBar {...dummyProps} masterProgress="error"/>))
        const taskbar = screen.getByTestId("taskbar")
        expect(taskbar).toBeInTheDocument()
    })
    it('renders the VFTaskBar with masterProgress=uploaded',()=>{
        render(contextWrapper(<VFTaskBar {...dummyProps} masterProgress="uploaded"/>))
        const taskbar = screen.getByTestId("taskbar")
        expect(taskbar).toBeInTheDocument()
    })
    it('renders the VFTaskBar with masterProgress=view',()=>{
        render(contextWrapper(<VFTaskBar {...dummyProps} masterProgress="view"/>))
        const taskbar = screen.getByTestId("taskbar")
        expect(taskbar).toBeInTheDocument()
    })
    it('renders the VFTaskBar with masterProgress=editOnline',()=>{
        render(contextWrapper(<VFTaskBar {...dummyProps} masterProgress="editOnline"/>))
        const taskbar = screen.getByTestId("taskbar")
        expect(taskbar).toBeInTheDocument()
    })
    // it('renders the VFTaskBar with masterProgress=error',()=>{
    //     render(contextWrapper(<VFTaskBar {...dummyProps} masterProgress="editOnlineSaved"/>))
    //     const taskbar = screen.getByTestId("taskbar")
    //     expect(taskbar).toBeInTheDocument()
    // })
    it('renders the VFTaskBar with masterProgress=uploaded',()=>{
        render(contextWrapper(<VFTaskBar {...dummyProps} masterProgress="editOnlineSubmitted"/>))
        const taskbar = screen.getByTestId("taskbar")
        expect(taskbar).toBeInTheDocument()
    })

    it('renders the VFTaskBar with masterProgress=view and editOnline=true',()=>{
        render(contextWrapper(<VFTaskBar {...dummyProps} masterProgress="view" editOnline/>))
        const taskbar = screen.getByTestId("taskbar")
        expect(taskbar).toBeInTheDocument()
    })

    it('renders the VFTaskBar with masterProgress=seasonality',()=>{
        render(contextWrapper(<VFTaskBar {...dummyProps} masterProgress="seasonality" editOnline/>))
        const taskbar = screen.getByTestId("taskbar")
        expect(taskbar).toBeInTheDocument()
    })

    it('renders the VFTaskBar with masterProgress=phaseInPhaseOut',()=>{
        render(contextWrapper(<VFTaskBar {...dummyProps} masterProgress="phaseInPhaseOut" editOnline/>))
        const taskbar = screen.getByTestId("taskbar")
        expect(taskbar).toBeInTheDocument()
    })
    
})