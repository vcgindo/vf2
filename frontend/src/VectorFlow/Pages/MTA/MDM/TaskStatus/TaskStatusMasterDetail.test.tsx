import { ReactNode } from "react";
import { fireEvent, render, screen } from "@testing-library/react"

import { UserDataContext } from "../../../../../context";
import TaskStatusMasterDetail from "./TaskStatusMasterDetail"

const dummyFn = jest.fn()

const contextWrapper = (children: ReactNode) => {
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
    );
  };

describe("TaskStatusMasterDetail Component",()=>{

    
    
    it("Renders the component",()=>{
        const dummyData = {
            TaskID: "1_20231206175429",
            PendingSince: "2023-12-06T17:59:01.667",
            TaskName: "M_SKU",
            Approver: "Approver1,Approver2",
            Requester: "Admin",
            TaskStatus: "Pending",
            Approvers: [
                {
                    TaskID: "1_20231206175429",
                    PendingSince: "2023-12-06T17:59:01.667",
                    TaskName: "M_SKU",
                    Approver: "Approver1",
                    Requester: "Admin",
                    TaskStatus: "Approved",
                    ApprovedDate: "2023-12-06T17:59:01.667",
                    ApproverId: "1"
                },
                {
                    TaskID: "1_20231206175429",
                    PendingSince: "2023-12-06T17:59:01.667",
                    TaskName: "M_SKU",
                    Approver: "Approver2",
                    Requester: "Admin",
                    TaskStatus: "Pending",
                    ApproverId: "2"
                },
                {
                    TaskID: "1_20231206175429",
                    PendingSince: "2023-12-06T17:59:01.667",
                    TaskName: "M_SKU",
                    Approver: "Approver2",
                    Requester: "Admin",
                    TaskStatus: "DB Updated",
                    ApproverId: "2"
                }
            ]
        }
        render(contextWrapper(<TaskStatusMasterDetail data={dummyData} onDownload={dummyFn}/>))
        const taskStatusMasterDetailComponent = screen.getByTestId('task-status-master-detail')
        const downloadBtn  = screen.getAllByText('Download')[0]
        fireEvent.click(downloadBtn)
        expect(taskStatusMasterDetailComponent).toBeInTheDocument()
    })
    it("Renders the component with individual approver",()=>{
        const dummyData = {
            TaskID: "1_20231206175429",
            PendingSince: "2023-12-06T17:59:01.667",
            TaskName: "M_SKU",
            Approver: "Approver1,Approver2",
            Requester: "Admin",
            TaskStatus: "Pending",
            Approvers: [
                {
                    TaskID: "1_20231206175429",
                    PendingSince: "2023-12-06T17:59:01.667",
                    TaskName: "M_SKU",
                    Approver: "Approver1",
                    Requester: "Admin",
                    TaskStatus: "Pending",
                    ApproverId: "1"
                },
                {
                    TaskID: "1_20231206175429",
                    PendingSince: "2023-12-06T17:59:01.667",
                    TaskName: "M_SKU",
                    Approver: "Approver2",
                    Requester: "Admin",
                    TaskStatus: "Pending",
                    ApproverId: "2"
                }
            ]
        }
        render(contextWrapper(<TaskStatusMasterDetail data={dummyData} onDownload={dummyFn}/>))

    })
    it("Renders the component with individual approver",()=>{
        const dummyData = {
            TaskID: "1_20231206175429",
            PendingSince: "2023-12-06T17:59:01.667",
            TaskName: "M_SKU",
            Approver: "Approver1,Approver2",
            Requester: "Admin",
            TaskStatus: "Pending",
            Approvers: [
                {
                    TaskID: "1_20231206175429",
                    PendingSince: "2023-12-06T17:59:01.667",
                    TaskName: "M_SKU",
                    Approver: "Approver1",
                    Requester: "Admin",
                    TaskStatus: "Pending",
                    ApproverId: "1"
                },
                {
                    TaskID: "1_20231206175429",
                    PendingSince: "2023-12-06T17:59:01.667",
                    TaskName: "M_SKU",
                    Approver: "Approver2",
                    Requester: "Admin",
                    TaskStatus: "Pending",
                    ApproverId: "2"
                }
            ]
        }
        render(contextWrapper(<TaskStatusMasterDetail data={dummyData} onDownload={dummyFn}/>))

    })
})