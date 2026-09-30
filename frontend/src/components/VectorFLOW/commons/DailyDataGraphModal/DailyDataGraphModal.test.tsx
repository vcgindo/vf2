import { screen, render, fireEvent, waitFor } from "@testing-library/react"
import DailyDataGraphModal from ".";
import { QueryClientProvider } from "@tanstack/react-query";
import { UserDataContext } from "../../../../context";
import { setupReactQuery } from "../../../../config/react-query-config";
import {ReactNode} from 'react'
import { GetDailyDataMockResponse } from "../../../../mock-data/BPR";
import {select} from 'react-select-event'
import { Provider } from "react-redux";
import {store} from '../../../../redux/store/store'

const queryClient = setupReactQuery();

const dummyRowData = {
    "tags": "PIPO",
    "SKUCode": "ARES0798C004",
    "SKUName": "AR CORE SHIRTS, 42",
    "WhCode": "2224",
    "WhName": "Sharath|HYD",
    "ParentWhCode": "9020_EBO",
    "ParentName": "Arrow EBO",
    "Norm": 3,
    "Stock": 3,
    "TechPen": 0,
    "TechColor": "Green",
    "TechColorSequence": 4,
    "GIT": 0,
    "EcoPen": 0,
    "EcoColor": "Green",
    "EcoColorSequence": 4,
    "PhaseIn-Out": 0,
    "ResidualSnP": 0,
    "NormReq": 0,
    "BlueReq": 0,
    "Req": 0,
    "RationedQTY": 0,
    "LeftoverParentStock": 0,
    "FGRMFlag": null,
    "SKULocAttr1": "ARES0798C",
    "SKULocAttr2": "42",
    "SKULocAttr3": "AR",
    "SKULocAttr4": "SH",
    "SKULocAttr5": "",
    "SKULocAttr6": "",
    "SKULocAttr7": null,
    "SKULocAttr8": null,
    "SKULocAttr9": null,
    "SKULocAttr10": "ARES0798C2224",
    "SKULocAttr11": "Yes",
    "SKULocAttr12": "Nov-22",
    "SKULocAttr13": "PIPO",
    "SKULocAttr14": "",
    "SKULocAttr15": "",
    "transit": [
        {
            "lc": "2224ARES",
            "cd": "2024-02-14",
            "slt": 10,
            "tlt": 9,
            "ag": 10,
            "eta": "2024-02-24",
            "cl": "2109297004",
            "qty": 50,
            "remarks": "Testing to be done fro bpr, for POC which will enable us to proceed with BPR"
        },
        {
            "lc": "2087ARES",
            "cd": "2024-02-15",
            "slt": 8,
            "tlt": 7,
            "ag": 8,
            "eta": "2024-02-25",
            "cl": "2177297004",
            "qty": 46,
            "remarks": "Testing to be done fro bpr, for POC which will enable us to proceed with BPR"
        },
        {
            "lc": "2108ARES",
            "cd": "2024-02-16",
            "slt": 10,
            "tlt": 9,
            "ag": 10,
            "eta": "2024-02-26",
            "cl": "2107019002",
            "qty": 50,
            "remarks": "Testing to be done fro bpr, for POC which will enable us to proceed with BPR"
        },
        {
            "lc": "2178ARES",
            "cd": "2024-02-17",
            "slt": 10,
            "tlt": 9,
            "ag": 10,
            "eta": "2024-02-27",
            "cl": "2147297006",
            "qty": 50,
            "remarks": "Testing to be done fro bpr, for POC which will enable us to proceed with BPR"
        },
        {
            "lc": "2048ARES",
            "cd": "2024-02-18",
            "slt": 9,
            "tlt": 8,
            "ag": 9,
            "eta": "2024-02-28",
            "cl": "417349A003",
            "qty": 48,
            "remarks": "Testing to be done fro bpr, for POC which will enable us to proceed with BPR"
        },
        {
            "lc": "2177ARES",
            "cd": "2024-02-19",
            "slt": 10,
            "tlt": 9,
            "ag": 10,
            "eta": "2024-02-29",
            "cl": "2107019003",
            "qty": 50,
            "remarks": "Testing to be done fro bpr, for POC which will enable us to proceed with BPR"
        },
        {
            "lc": "2224ARES",
            "cd": "2024-02-20",
            "slt": 8,
            "tlt": 7,
            "ag": 8,
            "eta": "2024-03-01",
            "cl": "2108019003",
            "qty": 46,
            "remarks": "Testing to be done fro bpr, for POC which will enable us to proceed with BPR"
        },
        {
            "lc": "2177AREK",
            "cd": "2024-02-21",
            "slt": 10,
            "tlt": 9,
            "ag": 10,
            "eta": "2024-03-02",
            "cl": "2109019003",
            "qty": 50,
            "remarks": "Testing to be done fro bpr, for POC which will enable us to proceed with BPR"
        },
        {
            "lc": "2211AREK",
            "cd": "2024-02-22",
            "slt": 10,
            "tlt": 9,
            "ag": 10,
            "eta": "2024-03-03",
            "cl": "2107019004",
            "qty": 50,
            "remarks": "Testing to be done fro bpr, for POC which will enable us to proceed with BPR"
        },
        {
            "lc": "2220AREK",
            "cd": "2024-02-23",
            "slt": 8,
            "tlt": 7,
            "ag": 8,
            "eta": "2024-03-04",
            "cl": "2108019004",
            "qty": 46,
            "remarks": "Testing to be done fro bpr, for POC which will enable us to proceed with BPR"
        }
    ]
}

const dummyprops = {
    rowData:dummyRowData,
    chartData:GetDailyDataMockResponse.data.dailyData,
    normChangeData:GetDailyDataMockResponse.data.normChangeHistory,
    masterData:GetDailyDataMockResponse.data.MasterData,
    suggestionData:GetDailyDataMockResponse.data.SuggestionHistoryData,
    monitoringData:GetDailyDataMockResponse.data.MonitoringData,
    isModalOpen:true,
    skuKey:'sc',
    whKey:'wc'
}

jest.mock("ag-charts-react", () => ({
    AgCharts: jest.fn(() => null)
  }));

const contextWrapper = (children: ReactNode,store:any) => {
    return (
      <QueryClientProvider client={queryClient}>
        <Provider store={store}>
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
        </Provider>
      </QueryClientProvider>
    );
  }

  describe("Renders Daily Data Graph",()=>{

    global.ResizeObserver = class MockedResizeObserver {
        observe = jest.fn();
        unobserve = jest.fn();
        disconnect = jest.fn();
      };

    it('Renders the Daily Data Modal',()=>{
        render(contextWrapper(<DailyDataGraphModal {...dummyprops}></DailyDataGraphModal>,store))
    })

    it('Opens the Norm Change History Table',async ()=>{
        render(contextWrapper(<DailyDataGraphModal {...dummyprops}></DailyDataGraphModal>,store))
        const clickToViewBtn = screen.getByText('Click To View');
        await waitFor(()=>{
            fireEvent.click(clickToViewBtn)
        })
    })

    it('Changes the Horizon',async ()=>{
        const {getByRole} = render(contextWrapper(<DailyDataGraphModal {...dummyprops}></DailyDataGraphModal>,store))
        const inputRange = getByRole('slider');
        fireEvent.change(inputRange, { target: { value: '75' } });
    })

    it('Selects Suspension Type',async ()=>{
        const {getAllByRole} = render(contextWrapper(<DailyDataGraphModal {...dummyprops}></DailyDataGraphModal>,store))
        await waitFor(async () => {
            const reactSelect = getAllByRole('combobox')[0]
            expect(reactSelect).toBeInTheDocument();
            await select(reactSelect, ['Upward Stock Based']);
        });
        await waitFor(async () => {
            const reactSelect = getAllByRole('combobox')[0]
            expect(reactSelect).toBeInTheDocument();
            await select(reactSelect, ['Downward Stock Based']);
        });
        await waitFor(async () => {
            const reactSelect = getAllByRole('combobox')[0]
            expect(reactSelect).toBeInTheDocument();
            await select(reactSelect, ['Upward Consumption Based']);
        });
        await waitFor(async () => {
            const reactSelect = getAllByRole('combobox')[0]
            expect(reactSelect).toBeInTheDocument();
            await select(reactSelect, ['Downward Consumption Based']);
        });
        })
        
        

  })
  




