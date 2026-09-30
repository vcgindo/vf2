import { fireEvent, render, screen,waitFor } from "@testing-library/react";
import VFMultiFilter from ".";
import { QueryClientProvider } from "@tanstack/react-query";
import { UserDataContext } from "../../../../context";
import { setupReactQuery } from "../../../../config/react-query-config";
import {ReactNode} from 'react'
import { useGetAllSKUs, useGetAllLocations } from "../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR";
import {GetAllSKUsMockResponse, GetAllLocationsMockResponse} from '../../../../mock-data/BPR'



const mockFunction = jest.fn()

const queryClient = setupReactQuery()

jest.mock("../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR");



const contextWrapper = (children: ReactNode) => {
    return (
      <QueryClientProvider client={queryClient}>
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
      </QueryClientProvider>
    );
  }
  

const useGetAllSKUMock = useGetAllSKUs as jest.MockedFunction<
    typeof useGetAllSKUs
>;

const useGetAllLocationsMock = useGetAllLocations as jest.MockedFunction<
    typeof useGetAllLocations
>;

const dummyprops={
    isFilterOpen:true,
    onApplyFilter:mockFunction,
    onGoBack:mockFunction,
    onChangeHorizon:mockFunction,
    selectedOption:mockFunction,
    toggleAdd:mockFunction,
    supplyChainForLocationCheckBoxList:[
        { label: 'Plant', id: '1' },
        { label: 'Supplier', id: '2' },
        { label: 'CWH', id: '3' },
        { label: 'RWH', id: '4' },
        { label: 'Depot', id: '5' },
        { label: 'Distributor', id: '6' },
        { label: 'Retailer', id: '7' }   
    ], 
    supplyChainForChildrenOfCheckBoxList:[
        { label: 'Plant', id: '1' },
        { label: 'Supplier', id: '2' },
        { label: 'CWH', id: '3' },
        { label: 'RWH', id: '4' },
        { label: 'Depot', id: '5' },
        { label: 'Distributor', id: '6' },
        { label: 'Retailer', id: '7' }   
    ],
    placeholder:"hello",
    supplyChainNodeFilterActive:true,
    locationFilterActive:true,
    productFilterActive:true,
    availabilityFilterActive:true,
    colorFilterActive:true,
    generalFilter:true,
    coverageFilterActive:true,
    horizonActive:true,
    currentTab:'both',
    headerText: "Header",
    headerIcon: '/assets/img/VectorFLOW/NMS/select-filter.svg',
    multiFilter: {
        supplyChainFilter:{
            id:'1',
            label:'SupplyChain',
            filters:[  
                // {name: 'SCF2',attributeName: "ForLocationLocationCode",value: "GW04",operator: "=", },
                {
                    "attributeName": "ForLocation",
                    "value": "2013",
                    "operator": "=",
                    "label": "ForLocation",
                    "name": "SCF1"
                },
        ]
        },
        locationFilter:{
            id:'2',
            label:'Location',
            filters:[
            //  { name:'LF1',attributeName: "l2",value: "11",operator: "doesnotcontain"},
            {
                "attributeName": "l3",
                "value": "l1",
                "operator": "doesnotcontain",
                "label": "WH Type",
                "name": "LF1"
            }
        ]
        },
        productFilter:{
            id:'3',
            label:'Product',
            filters:[
            // { name: 'PF1', attributeName: 'Attribute 1', value: 'Value 1',operator:">" },
            // { name: 'PF9', attributeName: 'Attribute 1', value: 'Value 1',operator:">" },
                {
                    "attributeName": "p1",
                    "value": "B",
                    "operator": "doesnotcontain",
                    "label": "Business",
                    "name": "PF1"
                },
                {
                    "attributeName": "p2",
                    "value": "B",
                    "operator": "doesnotcontain",
                    "label": "Category",
                    "name": "PF2"
                }

            
            ]
        },
        availabilityFilter:{
            id:'4',
            label:'Availability',
              filters: [
                    // { name: 'AF5', attributeName: 'Attribute 1', value: 'Value 1',operator:">" },
                    // { name: 'AF6', attributeName: 'Attribute 2', value: 'Value 2',operator:"<"  },
                    // { name: 'AF7', attributeName: 'Attribute 2', value: 'Value 2',operator:"<"  },
                    // {name:"AF5",attributeName: "PIPO,Seasonality", value: "Green",operator: "="}
                        {
                            "attributeName": "Norm",
                            "value": "2",
                            "operator": "greaterthan",
                            "label": "Norm",
                            "name": "AF1"
                        },
                        {
                            "attributeName": "Stock",
                            "value": "3",
                            "operator": "smallerthan",
                            "label": "Stock",
                            "name": "AF2"
                        },
                        {
                            "attributeName": "Git",
                            "value": "10",
                            "operator": "notequalto",
                            "label": "Git",
                            "name": "AF3"
                        },
                        {
                            "attributeName": "Availability",
                            "value": "0",
                            "operator": "equalto",
                            "label": "Availabilty",
                            "name": "AF4"
                        }

                ]
        },
        coverageFilter:{
            id:'5',
            label:'Coverage',
            filters:[]
        },
        colorFilter:{
            id:'6',
            label:'Color',
            filters:[
                // {name:'CF2',type: "colorage",attributeName: "black/red",value: "100",operator: "startswith"}
                {
                    "type": "colorcount",
                    "attributeName": "black",
                    "value": "2",
                    "operator": "equalto",
                    "label": "",
                    "name": "CF1"
                }
            ]
        },
        generalFilter:{
            id:'7',
            label:'General',
            filters:[
                // {name:'CF2',type: "colorage",attributeName: "black/red",value: "100",operator: "startswith"}
                {
                    "attributeName": "SKUCode",
                    "value": "22",
                    "operator": "equalto",
                    "label": "SKUCode",
                    "name": "GF1"
                }
            ]
        },
        customAttributeFilter:{
            id:'8',
            label:'Attribute',
            filters:[]
        },
        horizonFilter:{
            id:'9',
            label:'Horizon',
            filters:[]
        },
    },
    setMultiFilter:mockFunction,  
}


describe("VFMultiFilter Component", () => {
    global.ResizeObserver = class MockedResizeObserver {
        observe = jest.fn();
        unobserve = jest.fn();
        disconnect = jest.fn();
      };
    beforeEach(()=>{
       
        useGetAllSKUMock.mockImplementation(():any=>{
            return {data:{data:GetAllSKUsMockResponse},isLoading:false}
        })

        useGetAllLocationsMock.mockImplementation(():any=>{
            return {data:{data:GetAllLocationsMockResponse},isLoading:false}
        })
    })
     
   

    it('Handles all checkboxes',async()=>{
        render(contextWrapper(<VFMultiFilter {...dummyprops}></VFMultiFilter>))
        const checkboxes = screen.getAllByRole('checkbox')

        await waitFor(async () => {

        checkboxes.forEach((checkbox:any)=>{
            fireEvent.click(checkbox)
        })
      
    })
    checkboxes.forEach((checkbox:any)=>{
        fireEvent.change(checkbox, {target:{checked:false}})

    })
           
    })

    it('Handles all dropdowns',()=>{
        render(contextWrapper(<VFMultiFilter {...dummyprops}></VFMultiFilter>))

        const dropdowns = screen.getAllByRole('combobox')
        dropdowns.forEach((dropdown:any)=>{
            fireEvent.change(dropdown,{target:{value:'bfbf'}})
        })
        dropdowns.forEach((dropdown:any)=>{
            fireEvent.change(dropdown,{target:{value:'hfsafbshfa'}})
        })
    })

    it('Handles all input value',()=>{
        render(contextWrapper(<VFMultiFilter {...dummyprops}></VFMultiFilter>))

        const inputs = screen.getAllByPlaceholderText('Value')
        inputs.forEach((input:any)=>{
            fireEvent.change(input,{target:{value:'fsafa'}})
        })
        inputs.forEach((input:any)=>{
            fireEvent.change(input,{target:{value:'bfksabfksafkbk'}})
        })
    })

    it('handles open animation', ()=>{
        render(contextWrapper(<VFMultiFilter {...dummyprops}></VFMultiFilter>))
        const openanimation=screen.getAllByTestId('down-arrow')
        openanimation.forEach((open:any)=>{
            fireEvent.click(open)
        })
        openanimation.forEach((open:any)=>{
            fireEvent.click(open)
        })
    })

    

    it("renders all the filters in the component", () => {
            render(contextWrapper(<VFMultiFilter {...dummyprops}></VFMultiFilter>))
            const supplyChainNodeFilter=screen.getByTestId("supplyChainNodeFilter");
            expect(supplyChainNodeFilter).toBeInTheDocument()
            const productFilter=screen.getByTestId("productFilter");
            expect(productFilter).toBeInTheDocument()
            const availabilityFilter=screen.getByTestId("availabilityFilter");
            expect(availabilityFilter).toBeInTheDocument()
            const locationFilter=screen.getByTestId("locationFilter");
            expect(locationFilter).toBeInTheDocument()
            const coverageFilter=screen.getByTestId("coverageFilter");
            expect(coverageFilter).toBeInTheDocument()
            const colorFilter=screen.getByTestId("colorFilter");
            expect(colorFilter).toBeInTheDocument()
            const horizonActive=screen.getByTestId('horizonActive');
            expect(horizonActive).toBeInTheDocument()
        })

        it('Handles horizon interactions',()=>{
            render(contextWrapper(<VFMultiFilter {...dummyprops}></VFMultiFilter>))
            const rangeInput = screen.getByRole('slider');
            fireEvent.change(rangeInput, { target: { value: '60' } });
            fireEvent.change(rangeInput, { target: { value: '90' } });
        })

        it('Clicks on all buttons',()=>{
            render(contextWrapper(<VFMultiFilter {...dummyprops}></VFMultiFilter>))
            const resetButton = screen.getByText("Reset Filters");
            expect(resetButton).toBeInTheDocument()
            fireEvent.click(resetButton)
            const applybutton = screen.getByText("Apply Filter");
            fireEvent.click(applybutton)
            expect(applybutton).toBeInTheDocument();
        })

        // it('handles multiselect',async()=>{
        //     render(contextWrapper(<VFMultiFilter {...dummyprops}></VFMultiFilter>))
          
        //     const forLocation=screen.getByText('For Locations')
        //     expect(forLocation).toBeInTheDocument()
        //     fireEvent.click(forLocation)
          

           
        //     await waitFor(async () => {
        //         const reactSelect = screen.getAllByLabelText("Example Label")[0];
        //         expect(reactSelect).toBeInTheDocument();
        //         await select(reactSelect, ["ARES1136A004"]);
        //     });

        //     await waitFor(async () => {
        //         const reactSelect = screen.getAllByLabelText("Example Label")[1];
        //         expect(reactSelect).toBeInTheDocument();
        //         await select(reactSelect, ["ARES1136A004"]);
        //     });


        //     await waitFor(async () => {
        //         const reactSelect = screen.getAllByLabelText("Example Label")[2];
        //         expect(reactSelect).toBeInTheDocument();
        //         await select(reactSelect, ["ARES1136A004"]);
        //     });
            
        //     await waitFor(async () => {
        //         const reactSelect = screen.getAllByLabelText("Example Label")[3];
        //         expect(reactSelect).toBeInTheDocument();
        //         await select(reactSelect, ["ARES1136A004"]);
        //     });

        //     await waitFor(async () => {
        //         const reactSelect = screen.getAllByLabelText("Example Label")[4];
        //         expect(reactSelect).toBeInTheDocument();
        //         await select(reactSelect, ["ARES1136A004"]);
        //     });

        //     fireEvent.click(forLocation)

        //     const forChildren=screen.getByText('For Children Of')
        //     expect(forChildren).toBeInTheDocument()
        //     fireEvent.click(forChildren)

        //     await waitFor(async () => {
        //         const reactSelect = screen.getAllByLabelText("Example Label")[0];
        //         expect(reactSelect).toBeInTheDocument();
        //         await select(reactSelect, ["ARES1136A004"]);
        //     });

        //     await waitFor(async () => {
        //         const reactSelect = screen.getAllByLabelText("Example Label")[1];
        //         expect(reactSelect).toBeInTheDocument();
        //         await select(reactSelect, ["ARES1136A004"]);
        //     });

        // })

        

        // it('handles comparision',async ()=>{
        //     render(contextWrapper(<VFMultiFilter {...dummyprops}></VFMultiFilter>))
        //         await waitFor(async () => {
        //             const reactSelect = screen.getAllByLabelText("PF1")[0];
        //             expect(reactSelect).toBeInTheDocument();
        //             await select(reactSelect, ["P1"]);
        //             await select(reactSelect, ["P3"]);
        //         });
        //         await waitFor(async () => {
        //             const reactSelect = screen.getAllByLabelText("PF1")[1];
        //             expect(reactSelect).toBeInTheDocument();
        //             await select(reactSelect, ["="]);
        //             await select(reactSelect, ["="]);


        //         });
        //         await waitFor(async () => {
        //             const reactSelect = screen.getAllByLabelText("PF1")[1];
        //             expect(reactSelect).toBeInTheDocument();
        //             await select(reactSelect, ["="]);
        //             await select(reactSelect, ["="]);


        //         });

                
        //         await waitFor(async () => {
        //             const reactSelect = screen.getAllByLabelText("CF1")[0];
        //             expect(reactSelect).toBeInTheDocument();
        //             await select(reactSelect, ["Type"]);
        //         });
        //         await waitFor(async () => {
        //             const reactSelect = screen.getAllByLabelText("CF1")[1];
        //             expect(reactSelect).toBeInTheDocument();
        //             await select(reactSelect, ["Color"]);
        //         });
        // })


  
 }) 


