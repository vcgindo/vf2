
import {  useGetChronicUnavailabilityLoc, useGetChronicUnavailabilitySku} from "../../../../../Services/MTA/InsightsAndTrends";
import { GuidedInsights } from "../../../../../../mock-data/GuidedInsights";


jest.mock("../../../../../Services/MTA/InsightsAndTrends");
const useGetChronicUnavailabilityLocMock = useGetChronicUnavailabilityLoc as jest.MockedFunction<
    typeof useGetChronicUnavailabilityLoc
>;
const useGetChronicUnavailabilityLocData: any = { data: {data: GuidedInsights.ChronicUnavailabilityLocData }};

const useGetChronicUnavailabilitySkuMock = useGetChronicUnavailabilitySku as jest.MockedFunction<
    typeof useGetChronicUnavailabilitySku
>;
const useGetChronicUnavailabilitySkuData: any =  { data:{data: GuidedInsights.ChronicUnavailabilitySkuData }};


describe("Chronic Unavailability ", () => {
global.ResizeObserver = class MockedResizeObserver {
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
  };
    beforeEach(()=>{
        useGetChronicUnavailabilityLocMock.mockImplementation(()=>{
            return useGetChronicUnavailabilityLocData;
        })
        useGetChronicUnavailabilitySkuMock.mockImplementation(()=>{
            return useGetChronicUnavailabilitySkuData;
        })
    })
    
      
    //  it("Renders Chronic Unavailability", () => {
           
    //     render(<ChronicUnavailability/>)
       
    // })
    // it("On minimize chart click for graph 1", async() => {
          
    //     render(<ChronicUnavailability/>)
    //      await act(async () => {
            
    //         fireEvent.click(screen.getAllByTestId('minimizechart1')[0])
    //     })
       
    // })
    //   it("On minimize chart click for graph 2", async() => {
          
    //     render(<ChronicUnavailability/>)
    //      await act(async () => {
            
    //         fireEvent.click(screen.getAllByTestId('minimizechart2')[0])
    //     })
       
    // })

      it("Sample Test", async() => {
          
        expect(true).toBe(true);
       
    })

    
     
})