import { screen, render, fireEvent } from "@testing-library/react"
import { ReactNode } from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter as Router } from "react-router-dom"
import { Provider } from "react-redux"
import { store } from "../../../../redux/store/store"
import { UserDataContext } from "../../../../context"
import SelectGroupedMasters, { SelectGroupedMastersProps } from "."
import { setupReactQuery } from "../../../../config/react-query-config"

const mockFunction = jest.fn()

const dummyprops:SelectGroupedMastersProps = {
    selectedOptions:[],
    options:[],
    shouldShowMaster:()=>true,
    shouldShowMasterGroup:()=>true,
    onSubmit:mockFunction,
    onCancel:mockFunction,
    handleOnClickMaster:mockFunction,
    text:'hello',
    selectedMasters:[
      {
          "id": 5,
          "name": "MOQMaster",
          "fields": [
              {
                  "displayName": "SKUCode",
                  "key": "sk",
                  "visible": true,
                  "isAdd": false,
                  "isEdit": false,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "WhCode",
                  "key": "wh",
                  "visible": true,
                  "isAdd": false,
                  "isEdit": false,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "SupplierCode",
                  "key": "sc",
                  "visible": false,
                  "isAdd": false,
                  "isEdit": false,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "MOQ",
                  "key": "mq",
                  "visible": true,
                  "isAdd": false,
                  "isEdit": false,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              }
          ],
          "filters": [
              {
                  "id": "PusfrSatKf",
                  "masterId": 5,
                  "field": "",
                  "operator": "",
                  "text": ""
              }
          ],
          "colDefs": [
              {
                  "field": "sk",
                  "colId": "sk",
                  "headerName": "SKUCode",
                  "hide": false,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "wh",
                  "colId": "wh",
                  "headerName": "WhCode",
                  "hide": false,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "sc",
                  "colId": "sc",
                  "headerName": "SupplierCode",
                  "hide": true,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "mq",
                  "colId": "mq",
                  "headerName": "MOQ",
                  "hide": false,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              }
          ],
          "rowData": [],
          isChecked:true,
          "progress": "default"
      }
    ],

    allMasters:[
      {
          "id": 1,
          "name": "SKUMaster",
          "fields": [
              {
                  "displayName": "SKUCode",
                  "key": "sc",
                  "visible": true,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "Description",
                  "key": "sd",
                  "visible": false,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "ElephantOrderCapping",
                  "key": "ec",
                  "visible": true,
                  "isAdd": true,
                  "isEdit": false,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "Weight",
                  "key": "wt",
                  "visible": false,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "Volume",
                  "key": "vm",
                  "visible": false,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "c1",
                  "key": "c1",
                  "visible": true,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "c2",
                  "key": "c2",
                  "visible": false,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "c3",
                  "key": "c3",
                  "visible": true,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "c4",
                  "key": "c4",
                  "visible": true,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "c5",
                  "key": "c5",
                  "visible": true,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "c6",
                  "key": "c6",
                  "visible": true,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "c7",
                  "key": "c7",
                  "visible": false,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "c8",
                  "key": "c8",
                  "visible": false,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "c9",
                  "key": "c9",
                  "visible": false,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "c10",
                  "key": "c10",
                  "visible": false,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "c11",
                  "key": "c11",
                  "visible": false,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "c12",
                  "key": "c12",
                  "visible": false,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "c13",
                  "key": "c13",
                  "visible": false,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "c14",
                  "key": "c14",
                  "visible": false,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "c15",
                  "key": "c15",
                  "visible": false,
                  "isAdd": true,
                  "isEdit": true,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              }
          ],
          "filters": [
              {
                  "id": "L20AEYJxWR",
                  "masterId": 1,
                  "field": "",
                  "operator": "",
                  "text": ""
              }
          ],
          "colDefs": [
              {
                  "field": "sc",
                  "colId": "sc",
                  "headerName": "SKUCode",
                  "hide": false,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "sd",
                  "colId": "sd",
                  "headerName": "Description",
                  "hide": true,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "ec",
                  "colId": "ec",
                  "headerName": "ElephantOrderCapping",
                  "hide": false,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "wt",
                  "colId": "wt",
                  "headerName": "Weight",
                  "hide": true,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "vm",
                  "colId": "vm",
                  "headerName": "Volume",
                  "hide": true,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "c1",
                  "colId": "c1",
                  "headerName": "c1",
                  "hide": false,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "c2",
                  "colId": "c2",
                  "headerName": "c2",
                  "hide": true,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "c3",
                  "colId": "c3",
                  "headerName": "c3",
                  "hide": false,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "c4",
                  "colId": "c4",
                  "headerName": "c4",
                  "hide": false,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "c5",
                  "colId": "c5",
                  "headerName": "c5",
                  "hide": false,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "c6",
                  "colId": "c6",
                  "headerName": "c6",
                  "hide": false,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "c7",
                  "colId": "c7",
                  "headerName": "c7",
                  "hide": true,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "c8",
                  "colId": "c8",
                  "headerName": "c8",
                  "hide": true,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "c9",
                  "colId": "c9",
                  "headerName": "c9",
                  "hide": true,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "c10",
                  "colId": "c10",
                  "headerName": "c10",
                  "hide": true,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "c11",
                  "colId": "c11",
                  "headerName": "c11",
                  "hide": true,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "c12",
                  "colId": "c12",
                  "headerName": "c12",
                  "hide": true,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "c13",
                  "colId": "c13",
                  "headerName": "c13",
                  "hide": true,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "c14",
                  "colId": "c14",
                  "headerName": "c14",
                  "hide": true,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "c15",
                  "colId": "c15",
                  "headerName": "c15",
                  "hide": true,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              }
          ],
          "rowData": [],
          isChecked:true,
          "progress": "default"
      },
      {
          "id": 5,
          "name": "MOQMaster",
          "fields": [
              {
                  "displayName": "SKUCode",
                  "key": "sk",
                  "visible": true,
                  "isAdd": false,
                  "isEdit": false,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "WhCode",
                  "key": "wh",
                  "visible": true,
                  "isAdd": false,
                  "isEdit": false,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "SupplierCode",
                  "key": "sc",
                  "visible": false,
                  "isAdd": false,
                  "isEdit": false,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              },
              {
                  "displayName": "MOQ",
                  "key": "mq",
                  "visible": true,
                  "isAdd": false,
                  "isEdit": false,
                  "isDownload": true,
                  "col_Position":'1',
                  "isApplicable":true,
                   dataType:'String'
              }
          ],
          "filters": [
              {
                  "id": "PusfrSatKf",
                  "masterId": 5,
                  "field": "",
                  "operator": "",
                  "text": ""
              }
          ],
          "colDefs": [
              {
                  "field": "sk",
                  "colId": "sk",
                  "headerName": "SKUCode",
                  "hide": false,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "wh",
                  "colId": "wh",
                  "headerName": "WhCode",
                  "hide": false,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "sc",
                  "colId": "sc",
                  "headerName": "SupplierCode",
                  "hide": true,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              },
              {
                  "field": "mq",
                  "colId": "mq",
                  "headerName": "MOQ",
                  "hide": false,
                  "floatingFilter": true,
                  "filter": "agMultiColumnFilter",
                  "minWidth": 180,
                  "cellStyle": {
                      "text-align": "center"
                  },
                  "flex": 1
              }
          ],
          "rowData": [],
          isChecked:true,
          "progress": "default"
      },
  ]
}

const queryClient = setupReactQuery()

const contextWrapper = (children: ReactNode,store:any) => {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Provider store={store}>
          <UserDataContext.Provider
            value={{
              user: { user: { theme_ui: "NOIRFUSION" } },
              changeColorTheme: (color:any) => {
                return color;
              },
              isSideBarOpen:true,toggleSideBar:jest.fn
            }}
          >
            {children}
          </UserDataContext.Provider>
        </Provider>
      </Router>
    </QueryClientProvider>
  );
}

describe("SelectGroupedMasters Component", () => {
  beforeEach(()=>{
    render(contextWrapper(<SelectGroupedMasters {...dummyprops}/>,store))
  })

    it("renders the component", () => {
      const submit=screen.getByText('Submit')
      expect(submit).toBeInTheDocument()
      const cancel=screen.getByText('Cancel')
      expect(cancel).toBeInTheDocument()
    //   const text=screen.getByText('hello')
    //   expect(text).toBeInTheDocument()
      });

      it("Check if page closes when Cancel button is clicked", async () => {
        const cancel = screen.getByText("Cancel");
        fireEvent.click(cancel);
        expect(mockFunction).toBeCalled()
      });

      it("Renders VFMasterGroupCardContent with default props", async () => {
        const masterNameElement = screen.getByText("MOQMaster");
        expect(masterNameElement).toBeInTheDocument();
      });

      it("Handles hover state on VFMasterGroupCardContent",()=>{
        const masterNameElement = document.querySelector("#SKUMaster") as HTMLElement;
        fireEvent.mouseEnter(masterNameElement);
        // expect(masterNameElement).toHaveStyle('backgroundColor: #820F4C');
        fireEvent.mouseOut(masterNameElement);
        expect(masterNameElement).toHaveStyle('backgroundColor: #FFFFF');
      }); 

      it("It handles Click on VFMasterGroupCardContent",()=>{
        const clickableElement = screen.getAllByTestId("vf-master-group-card")[0];
        fireEvent.click(clickableElement);
        fireEvent.click(clickableElement);
    })  
    
})
  
