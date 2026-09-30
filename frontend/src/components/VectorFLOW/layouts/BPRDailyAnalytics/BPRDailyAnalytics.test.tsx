import { render } from "@testing-library/react"
import BPRDailyAnalytics from "."
import { BrowserRouter as Router } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { Provider } from "react-redux";
import { setupReactQuery } from "../../../../config/react-query-config";
import { useGetAnalyticsData } from "../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR";
import { GetDailyAnalyticsMockResponse } from "../../../../mock-data/BPR";
import {store} from "./../../../../redux/store/store";

import {UserDataContext} from '../../../../context'


jest.mock('../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR')

const dummyProps = {
    colDefs:[
        {
          headerName:'',
          colId:'color'
        },
        {
          headerName:'On-Hand.'
        },
        {
          headerName:''
        },
        {
          headerName:'Pipeline.'
        },
        {
          headerName:''
        }
    ],
    rowData:[{"color":"Black","techCount":2345,"techChange":34,"ecoCount":3856,"ecoChange":-6},{"color":"Red","techCount":345,"techChange":23,"ecoCount":349,"ecoChange":-12},{"color":"Yellow","techCount":23,"techChange":-21,"ecoCount":123,"ecoChange":28},{"color":"Green","techCount":657,"techChange":-2,"ecoCount":453,"ecoChange":2},{"color":"Blue","techCount":345,"techChange":0,"ecoCount":1234,"ecoChange":-43},{"color":"White","techCount":2345,"techChange":12,"ecoCount":45,"ecoChange":0}]
}

const queryClient = setupReactQuery();

const contextWrapper = (children: any,store:any,theme:string) => {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Provider store={store}>
        <UserDataContext.Provider
            value={{
              user: { user: { theme_ui: theme } },
              changeColorTheme: (color) => {
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
};

const useGetAnalyticsDataMock = useGetAnalyticsData as jest.MockedFunction<
  typeof useGetAnalyticsData
>


describe("BPRDailyAnalytics",()=>{

  
  it("Renders the loader",()=>{
    useGetAnalyticsDataMock.mockImplementation(():any => {
      return {data: {data:GetDailyAnalyticsMockResponse},isLoading:true};
    });
      render(contextWrapper(<BPRDailyAnalytics {...dummyProps}/>,store,"NOIRFUSION"))
  })
 
    it("Renders the components with all types of data",()=>{
      useGetAnalyticsDataMock.mockImplementation(():any => {
        return {data: {data:GetDailyAnalyticsMockResponse},isLoading:false};
      });
        render(contextWrapper(<BPRDailyAnalytics {...dummyProps}/>,store,"REGALBLAZE"))
    })
})