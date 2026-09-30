import { render, screen,fireEvent} from '@testing-library/react';
import { UserDataContext } from "../../../../../context";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter as Router } from "react-router-dom";
import { setupReactQuery } from "../../../../../config/react-query-config";

import {GetBTRDataMockedResponse} from '../../../../../mock-data/BTR'

import { ReactNode } from "react";
import { Provider } from "react-redux";
import {store} from "../../../../../redux/store/store";
import { useGetBTRData, useGetBTRDataCount } from '../../../../../VectorFlow/Services/MTA/InsightsAndTrends/BTR';
import BufferTrendReport from '.';


// Mock context data

jest.mock('../../../../Services/MTA/InsightsAndTrends/BTR')

// const mockContextValue = {
//   user: { user: { theme_ui: "NOIRFUSION" } },
//   changeColorTheme: jest.fn(),
//   isSideBarOpen: true,
//   toggleSideBar: jest.fn()
// };

// Mock the query client
const queryClient = setupReactQuery();

const useGetBTRDataMock = useGetBTRData as jest.MockedFunction<
    typeof useGetBTRData
>

const useGetBTRDataCountMock = useGetBTRDataCount as jest.MockedFunction<
  typeof useGetBTRDataCount
>



  const contextWrapper = (children: ReactNode,store:any) => {
    return (
      <QueryClientProvider client={queryClient}>
        <Router>
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
        </Router>
      </QueryClientProvider>
    );
  };

describe('Research and insights Component', () => {
  global.ResizeObserver = class MockedResizeObserver {
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
  };

  beforeEach(() => {

    useGetBTRDataMock.mockImplementation(():any=>{
        return {
            mutateAsync:()=>{
              return {data:GetBTRDataMockedResponse}
            },
            isLoading:false
          }
    })

    useGetBTRDataCountMock.mockImplementation(():any=>{
      return{
        mutateAsync:()=>{
          return{
            data:{
              data:{
                "recordCount": null,
                "data": {
                    "EcoCount": "19109",
                    "TechCount": "19109"
                },
                "status": 200,
                "msg": null,
                "errorCount": null,
                "error": null,
                "conflictErrorCount": null,
                "conflictError": null
            }
            }
          }
        }
      }
    })



  });
  it('renders loader when isLoading is true', () => {
    useGetBTRDataMock.mockImplementation(():any=>{
        return {
            mutateAsync:()=>{
              return {data:GetBTRDataMockedResponse}
            },
            isLoading:true
          }
    })
      render(contextWrapper(<BufferTrendReport />,store));
        // expect(screen.getByTestId('loader')).toBeInTheDocument();
  });

  it('renders the component', () => {
      render(contextWrapper(<BufferTrendReport />,store));
  });

  it('handles interactions', () => {
    render(contextWrapper(<BufferTrendReport />,store));
    const horizontalToggleButton = screen.getByText('Horizontal View')
    fireEvent.click(horizontalToggleButton)

    const verticalToggleButton = screen.getByText('Vertical View')
    fireEvent.click(verticalToggleButton)

    const secondTab = screen.getByText('On-Hand Inv. View')
    fireEvent.click(secondTab)

    const thirdTab = screen.getByText('Pipeline Inv. View')
    fireEvent.click(thirdTab)
});

});


// describe('Handles all interactions', () => {
//   global.ResizeObserver = class MockedResizeObserver {
//     observe = jest.fn();
//     unobserve = jest.fn();
//     disconnect = jest.fn();
//   };

//   beforeEach(async() => {
//     cleanup()
//     useGetBPRUIConfigurationMock.mockImplementation(():any=>{
//         return {data: {data:GetBPRUIConfigurationMockResponse},isLoading:false};
//       })
  

//     useGetBPRDataMock.mockImplementation(():any=>{
//       return {
//         mutateAsync:()=>{
//           return {data:GetBPRDataMockResponse}
//         },
//         isLoading:false
//       }
//     })
    
//     render(contextWrapper(<ResearchInsights />,store));
    

//     // await waitFor(async()=>{
//     //   const skuCodeElement = screen.getAllByRole('gridcell', { name: /ARES0798C004/i })[0];
//     //   expect(skuCodeElement).toBeInTheDocument()
//     // })

//   });

 

//   it("Clicks on update graph when no row is selected",async()=>{
    
//     await waitFor(async()=>{
//       fireEvent.click(screen.getByText('Update Graph'))
//     })
//   })

//   it("Clicks on update graph when one row is selected",async()=>{
    
//     await waitFor(async()=>{
//       const checkboxInput = screen.getAllByLabelText('Press Space to toggle row selection (unchecked)')[0];
//       checkboxInput.click(); // Simulate a click to check the checkbox

//       fireEvent.click(screen.getByText('Update Graph'))

//       const ecoBtn = screen.getByText("Eco")
//       fireEvent.click(ecoBtn)

//       const rangeInput = screen.getByRole('slider');
//       fireEvent.change(rangeInput, { target: { value: '45' } });
//     })
//   })

//   it("Clicks on update graph when two rows are selected",async()=>{
    
//     await waitFor(async()=>{
//       const checkboxInput = screen.getAllByLabelText('Press Space to toggle row selection (unchecked)');
//       fireEvent.click(checkboxInput[0])
//       fireEvent.click(checkboxInput[1])
      
      
      
     
//     })
//   //   await waitFor(()=>{
      
//   //     const updateGraphBtn = screen.getByText('Update Graph')
//   //     updateGraphBtn.click()
//   //   })
//   //   await waitFor(()=>{
      
//   //     const canvasElement = screen.getAllByRole('canvas')[0];
//   //     expect(canvasElement).toBeInTheDocument()
//   //   })
   
//   })

  
// });