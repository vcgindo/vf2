import { AgCharts } from 'ag-charts-react'
import React, { useEffect, useMemo, useRef, useState, } from 'react'
import { useFetchFOLGap, useSaveRouteData } from '../../../../Services/MTO/Production/DynamicReleaseManagement'
import VFModalCard from '../../../../../components/VectorFLOW/commons/VFModalCard'
import RouteAssignment from '../RouteAssignment/RouteAssignment'
// import { DueDateContentWrapper, DueDateOptionDateText, DueDateOptionLabel, DueDateOptionLabelText, FOLGapCalculateContentWrapper } from './styles' // phase 2
import { FolGapContentWrapper, FolGapDetailDiv, FolGapDetailHeader, FolGapDetailHeaderInfo, FolGapDetailHeaderInfoMain, RouteContentWrapper, Text } from './styles'
import OverlayLoader from '../../Common/Loader'
import { notifyError, notifySuccess } from '../../../../../helpers/notify'
import VFButton from '../../../../../components/VectorFLOW/commons/VFButton'
import VFButtonOutline from '../../../../../components/VectorFLOW/commons/VFButtonOutline'
// import Radio from '../../../../../components/VectorFLOW/commons/MTO/Radio'  //phase 2
import _ from 'lodash'
import VFTable from '../../Common/VFTable';
import { GridOptions } from 'ag-grid-enterprise'
import { useGetCCRGroupMaster, useGetCCRItemTypeMappingMaster, useGetFOLData, useGetLineCCRDetails, useGetRouteDetails } from '../../../../../VectorFlow/Services/MTO/Production/DueDateQuotation'
import CustomLegend from '../CustomLegend'

const EditRouteModal = ({orderDetails, chartoptions, setChartOptions, onDataUpdateCallback, showModal, setShowModal, themeUi }: any) => {
    const { mutateAsync: getRouteDetails, isLoading: isGetRouteDetails } = useGetRouteDetails();
    const { mutateAsync: getCCRGroupMaster, isLoading: isGetCCRGroupMaster } = useGetCCRGroupMaster();
    const { mutateAsync: getCCRItemTypeMappingMaster, isLoading: isGetgetCCRItemTypeMappingMaster } = useGetCCRItemTypeMappingMaster();
    const { mutateAsync: getFOLData, isLoading: isGetFOLData } = useGetFOLData();
    const { mutateAsync: getLineCCRDetails, isLoading: isGetLineCCRDetails } = useGetLineCCRDetails();
    const { mutateAsync: saveRouteData, isLoading, isSuccess, isError } = useSaveRouteData();
    const { mutateAsync: fetchFolGapData, isLoading: isFetchFolGapData } = useFetchFOLGap();
    // const [selectedDueDates, setSelectedDueDates] = useState<any>([]); //phase 2
    const [CCRFOLGapDetails, setCCRFOLGapDetails] = useState<any>([]);
    const [CCROrderLoadDetails, setCCROrderLoadDetails] = useState<any>([]);
    const [isRouteChange, setIsRouteChange] = useState(false);
    const [showFOLGapDetails, setShowFOLGapDetails] = useState(false);
    const [lineCCR, setLineCCR] = useState<any>();
    const [masters, setMasters] = useState<any>({});
    const [route, setRoute] = useState<any>();
    const [previousOrderRoute, setPreviousOrderRoute] = useState<any>();
    const previousRouteRef = useRef<any[]>(route);
    // const [chartOptions, setChartOptions] = useState(chartoptions); // phase 2

    type Route = {
        ccrId: number;
        routeId: number;
        ccrGrpId: number;
        ps: number;
    };

    type LineCcr = {
        [order: string]: {
            [ccrId: string]: {
                load: number;
                pcqty: number;
                rid: number;
            };
        };
    };

    useEffect(() => {
        getMastersData();
    }, []);

    useEffect(() => {
        if (!_.isEmpty(masters)) {
            getRoute(orderDetails.routeNum, orderDetails.orderKey);
        }
      }, [masters]);

    useEffect(() => {
        if (isSuccess) {
            notifySuccess("Route updated successfully!")
        }
        if (isError) {
            notifyError("Failed to update route data")
        }
    }, [isSuccess, isError])

    useEffect(() => {
        if (isSuccess) {
            setShowModal(false);
        }
    }, [isSuccess]);

    const getMastersData = async () => {
        try {
            const CCRItemTypeMappingMaster = await getCCRItemTypeMappingMaster();
            if (CCRItemTypeMappingMaster?.status !== 200) {
                throw new Error("Failed to Fetch CCR Item Type Mapping Data");
            }
            const CCRItemTypeMappingMasterData = Object.values(CCRItemTypeMappingMaster?.data?.data);
    
            const ccrGroupMaster = await getCCRGroupMaster();
            if (ccrGroupMaster?.status !== 200) {
                throw new Error("Failed to Fetch CCR Item Type Mapping Data");
            }
            const ccrGroupData = Object.values(ccrGroupMaster?.data?.data);
            
            const ccrGroups: any = [];
            const FOLData = await getFOLData();
            if (FOLData?.status !== 200) {
                throw new Error("Failed to Fetch CCR Item Type Mapping Data");
            }
            const FOL = FOLData?.data?.data;
  
            ccrGroupData.forEach((group: any) => {
                const obj: any = { label: group.ccr_group_code, value: group.ccr_group_id, ccrs: [] }
                // let minFOL = Infinity
                let minFol = Infinity;
                let maxFol = -Infinity;
                group.ccrs.forEach((ccr: any) => {
                    minFol = Math.min(minFol, FOL[ccr.ccr_id]?.fol || 0);
                    maxFol = Math.max(maxFol, FOL[ccr.ccr_id]?.fol || 0)
                })
                group.ccrs.forEach((ccr: any) => {
                    obj.ccrs.push({ label: ccr.ccr_name, value: ccr.ccr_id, minFol, maxFol, fol: FOL[ccr.ccr_id]?.fol || 0, plant_id: ccr.plant });
                });
                ccrGroups.push(obj);
            });

            setMasters({ ccrGroups, CCRItemTypeMappingMaster: CCRItemTypeMappingMasterData });
        } catch (error) {
            console.log(error);
            notifyError("Failed to fetch CCR Details");
            setShowModal(false);
        }
    }

    const getRoute = async (route: any, orderKey: any) => {
    
        if (typeof route === "number") {
            try {
                const data = await getRouteDetails(route);
                if (data?.status != 200) {
                    throw new Error("Failed to fetch Route Details");
                }
                const routeDetails = data.data.data;
    
                routeDetails.sort((a: any, b: any) => a.ps - b.ps);
    
                const newRoute: any = [];
                routeDetails.forEach((routeDetail: any) => {
                    const obj = [];
    
                    const ccrGroup = masters.ccrGroups?.find((ccr: any) => ccr?.value === routeDetail?.ccrGrpId);
                    obj[0] = ccrGroup;
                    obj[1] = ccrGroup?.ccrs.find((ccr: any) => ccr?.value === routeDetail?.ccrId);
                    newRoute[routeDetail.ps - 1] = obj;
                });
    
                setPreviousOrderRoute(newRoute)
                setRoute(newRoute);
            } catch (error) {
                console.log(error);
                notifyError("Failed to fetch Route Details");
                setShowModal(false);
            }
        } else {
            // Handle cases where route is not a number
            setRoute(route);
        }
    
        if (orderKey) {
            try {
                const data = await getLineCCRDetails([orderKey]);
                setLineCCR(data.data.data)
            } catch (error) {
                console.log(error);
            }
        }
    }

    function convertToRequiredFormat(routes: Route[], lineCcr: LineCcr): any {
        const myCCRDetails: any = [];        
        const orderPendingCCRQty = orderDetails.pcqty || 0;
        
        routes.forEach((e: any, i) => {
            const CCRId = e[1].value;
            const lineCCRPendingQty = lineCcr[orderDetails?.orderKey]?.[CCRId]?.pcqty || 0;
            const CCRPendingQty = lineCCRPendingQty || orderPendingCCRQty;
            const ccrItem = masters?.CCRItemTypeMappingMaster.find((ccr: any) => ccr.ccrId === CCRId && ccr.it == orderDetails.itemTypeId);
            const orderLoad = Math.ceil(((ccrItem.tt || 0) * (CCRPendingQty && CCRPendingQty >= 0 ? CCRPendingQty : orderPendingCCRQty)));

            const perCCRDetail = {
                "ccrid": CCRId,
                "ccrgrp": e[0].value,
                "pcQty": CCRPendingQty,
                "pos": (i + 1).toString(),
                "ol": orderLoad || 0,
            }

            myCCRDetails.push(perCCRDetail);

        })

        let routeName = '';
        routes.forEach((e: any) => {
            routeName = routeName + (e[1].label) + '/'
        })
        if (routeName.length >= 1) {
            routeName = routeName.substring(0, routeName.length - 1);
        }

        const finalData = {
            "routeData": {
                "orders": [
                    {
                        "rid": orderDetails.routeNum,
                        "route": routeName,
                        "ok": orderDetails.orderKey,
                        "ccrdetails": myCCRDetails,
                        "ccr_fol_gap": CCRFOLGapDetails,
                        "ccr_order_load":CCROrderLoadDetails
                    }
                ]
            }
        }

        return finalData;

    }

    const SaveRoute = async () => {
        const data = convertToRequiredFormat(route, lineCCR);
        try {
            const response = await saveRouteData({ body: JSON.parse(JSON.stringify(data)), update_order_wip: 1 })
            if (response.status === 200) {
                onDataUpdateCallback();
                setShowModal(false);
            }
        }
        catch (error) {
            console.log(error)
        }
    }

    const calculateCCGroups = () => {

        // Get all CCRs that have mappings for the current item type
        const validCCRs = new Set<string>();
        masters?.CCRItemTypeMappingMaster?.forEach((mapping: any) => {
            if (mapping.it === orderDetails.itemTypeId) {
                validCCRs.add(mapping.ccrId);
            }
        });

        // Filter CCR groups based on valid CCRs and selected plant
        const filteredCCRGroups = masters?.ccrGroups?.map((ccrGroup: any) => {
            // Filter CCRs within each group
            const filteredCCRs = ccrGroup.ccrs.filter((ccr: any) => {
                return ccr.plant_id === orderDetails.plantId && validCCRs.has(ccr.value);
            });

            // Update the first index's CCRs with the filtered CCRs
            if (filteredCCRs.length > 0) {
                return {
                    ...ccrGroup,
                    ccrs: filteredCCRs
                };
            }
            return null;
        }).filter(Boolean); // Remove null entries

        return filteredCCRGroups || [];
    }
    
    const ccrGroups = useMemo(calculateCCGroups, [masters , orderDetails.plantId])

    /**
    * Determines if the save action should be disabled based on selected due dates.
    * 
    *  - Returns `true` if no due date is selected.
    *  - Returns `false` if at least one due date is selected.
    */
    const isSaveDisabled = useMemo(() => {
        if (!isRouteChange) {
            return true;
        }
        return !route.length || route.some((routeItem: any) => !routeItem[0] || !routeItem[1]);
    
        {/*
            
        //phase 2 changes
        if (selectedDueDates.length) {
            const hasSelectedDueDate = selectedDueDates.find((selectedDueDate: any) => selectedDueDate.selected == true);
            if (hasSelectedDueDate) {
                return false;
            } else {
                return true;
            }
        } else {
            return true;
        }
    }, [selectedDueDates]);
    */}
    }, [route, isRouteChange]);

    //compare route array with previous route
    function compareDataIgnoringFirst(arr1: any, arr2: any): boolean {
        if (arr1.length !== arr2.length) return false;
      
        return arr1.every((subArr1:any, i:any) => {
            const subArr2 = arr2[i];
            if (subArr1.length !== subArr2.length) return false;
      
            // Ignore first element (0th index)
            const slice1 = subArr1.slice(1);
            const slice2 = subArr2.slice(1);
      
            return JSON.stringify(slice1) === JSON.stringify(slice2);
        });
    }

    useEffect(() => {
         /**
         * This effect is triggered whenever the `route` dependency changes.
         * It compares the current route to a previously stored route to determine 
         * if there has been a change.
         *
         * If the route has changed:
         * - Sets the `isRouteChange` state to `true`.
         * - Clears the selected due dates by setting `selectedDueDates` to an empty array.
         */
        {/* phase 2
            // if (previousRouteRef?.current?.length > 0) {
        //     const hasChanged = !isEqual(previousRouteRef.current, route) && !isEqual(previousRouteRef.current,previousOrderRoute);
        //     if (hasChanged) {
        //         setIsRouteChange(true);
        //         // setSelectedDueDates([]); //phase 2
        //         setCCRFOLGapDetails([]);
        //     }
        // }
        // // Update previousRouteRef to the current route state
        // previousRouteRef.current = route;
        */}
        if (previousOrderRoute) {
            const hasChanged = !compareDataIgnoringFirst(previousOrderRoute, route);
            if (hasChanged) {
                setIsRouteChange(true);
                // setSelectedDueDates([]); //phase 2
                setCCRFOLGapDetails([]);
            } else {
                setIsRouteChange(false);
                setCCRFOLGapDetails([]);
            }
        }

    }, [route]);

    /**
    * Determines whether the "Calculate FOL Gap" button should be disabled.
    * 
    * The button is disabled if there are no changes to the route or 
    * if any route item is incomplete (missing either the start or end point).
    * @returns {boolean} - Returns `true` if the button should be disabled,
    *                      `false` otherwise.
    * phase 2
    */
    // const isCalculateFOLGapDisabled = useMemo(() => {
    //     if (!isRouteChange) {
    //         return true;
    //     }
    //     return !route.length || route.some((routeItem: any) => !routeItem[0] || !routeItem[1]);
    // }, [route, isRouteChange]);

    /**
    * Updates the selected state of due dates based on the provided due date type.
    *
    * This function maps over the previous state of `selectedDueDates` and
    * updates each due date's `selected` property. The due date with a
    * `dueDateType` that matches the provided `dueDateType` will have its
    * `selected` property set to `true`, while all others will be set to `false`.
    *
    * @param {string} dueDateType - The type of the due date to be selected.
    *                                This corresponds to the `dueDateType` property
    *                                of a specific due date within `selectedDueDates`.
    * phase 2
    */
    // const updateDueDate = useCallback((dueDateType: string) => {
    //     setSelectedDueDates((prevState: any) =>
    //         prevState.map((dueDate: any) => ({
    //             ...dueDate,
    //             selected: dueDate.dueDateType === dueDateType,
    //         }))
    //     );
    // }, [setSelectedDueDates]);


    /**
    * Fetch Fol Gap data and update the state with due dates.
    * 
    * The function handles data conversion, simulates an API call with mock response data, 
    * and processes the response to determine due dates and their properties (type, value, selection status,
    * disabled status, and label). Updates the due dates state based on response data.
    */
    const fetchFolGap = async () => {
        try {
            const data = convertToRequiredFormat(route, lineCCR);
            const response = await fetchFolGapData({ body: data });        
        
            if (response.status === 200) {

                {/* 
                    // phase 2 changes, dont remove
                const graphData = response.data.data?.graph_data;
                const convertedGraphData = convertData(graphData, true);
                setChartOptions(convertedGraphData);

                const dueDates: any = response.data.data?.due_date || {};
                const disableCrdd = new Date(dueDates.crdd) < new Date(dueDates.foldd);

                const newDueDates = Object.entries(dueDates).map(dueDate => ({
                    dueDateType: dueDate[0],
                    value: dueDate[1],
                    selected: dueDate[0] === "foldd" && disableCrdd ? true : false,
                    disabled: dueDate[0] === "crdd" ? disableCrdd : false,
                    label: dueDate[0] === "crdd" ? "Customer Requested Due Date" : "Fol Based Due Date",
                }));
                setSelectedDueDates(newDueDates);

                */}
                
                const CCRFOLGap = response.data.data?.ccr_fol_gap || {};
                const CCROrderLoad = response.data.data?.ccr_order_load || {};

                setCCROrderLoadDetails(CCROrderLoad)
                setCCRFOLGapDetails(CCRFOLGap);
                // setIsRouteChange(false);
                // setShowFOLGapDetails(true);
            }
        } catch (error) {
            console.error('Error fetching FOL gap:', error);
        }
    }
    
    const gridOptions: GridOptions<any> = {
        getRowStyle: (params: any) => {
            return {
                background: params.node.rowIndex % 2 === 0 ? "#F4F4F4" : "#FFFFFF",
            };
        },
        rowHeight: 28,
        defaultColDef: {
            minWidth: 100,
            flex: 1,
            initialFlex: 1,
            autoHeaderHeight: true,
            suppressMenu: true,
            filter: false,
            floatingFilter: false,
            enableRowGroup: false,
            enableValue: false,
            enablePivot: false,
            cellStyle: {
                "fontSize": "12px",
                'display': 'flex',
                'alignItems': 'center',
      
            },
        },
        columnDefs: [
            { colId: "ccrname", field: "ccrname", headerName: "CCR Name" },
            { colId: "fol_gap", field: "fol_gap", headerName: "Gap (in Days)" },
        ],
        sideBar: false,
        suppressAggFuncInHeader: true,
        suppressMakeColumnVisibleAfterUnGroup: true,
        suppressColumnVirtualisation: true,
        pivotMode: false,
        suppressMenuHide: true,
        suppressRowClickSelection: true,
        suppressPaginationPanel: true,
        rowSelection: undefined,
    };

    return (
        <VFModalCard openModal={showModal} closeModal={() => { setShowModal((false)) }} headerText={'Edit Route'} headerIcon={''} closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"} paddingLeftAndRight={0} headerTextColor={'black'} backgroundColor={'f4f4f4'} data-testid="vfmultifilter-img" >
            {isLoading && <OverlayLoader message='Saving route data' />}
            {(isFetchFolGapData || isGetRouteDetails || isGetFOLData || isGetLineCCRDetails || isGetCCRGroupMaster || isGetgetCCRItemTypeMappingMaster) && <OverlayLoader message='Loading, please wait ...' />}
            {showFOLGapDetails ?
                <FolGapContentWrapper>
                    <FolGapDetailHeader>
                        Are you sure you want to change the routes?
                    </FolGapDetailHeader>
                    <FolGapDetailHeaderInfo>
                        *This change will be permanent but will not have any effect on due dates
                    </FolGapDetailHeaderInfo>
                    <FolGapDetailDiv>
                        <FolGapDetailHeaderInfoMain>
                            A gap will be created in the FOL as follows:
                        </FolGapDetailHeaderInfoMain>

                        <VFTable
                            gridOptions={gridOptions}
                            rowData={CCRFOLGapDetails}
                            height={"100%"}
                            hideStatusBar={true}
                        />
                    </FolGapDetailDiv>
                    
                </FolGapContentWrapper>
                :
                <RouteContentWrapper>
                    <Text>
                        You can change route by selecting CCR from drop-down
                    </Text>
                    {
                        masters && ccrGroups && route &&

                        (<RouteAssignment
                            isEditable={true}
                            theme={themeUi}
                            ccrGroupMaster={ccrGroups}
                            selectedRoutes={route}
                            setSelectedRoutes={setRoute}
                            isCCRGroupEditable={false}
                        />)
                    }

                    {/*
                    // this is require in phase 2 development
                    <FOLGapCalculateContentWrapper>
                        <VFButton
                            onClick={() => { fetchFolGap() }}
                            themeUi={themeUi}
                            style={{
                                zoom: 0.7,
                                pointerEvents: isCalculateFOLGapDisabled ? "none" : "auto",
                                opacity: isCalculateFOLGapDisabled ? "0.5" : "",
                            }} >
                            Calculate
                        </VFButton>

                        {(selectedDueDates?.length > 0) && (
                            <DueDateContentWrapper>
                                {selectedDueDates.map((selectedDueDate: any) => {
                                    return (
                                        <DueDateOptionLabel
                                            key={selectedDueDate.dueDateType}
                                            isCRDDDisabled={selectedDueDate.disabled}>
                                            <Radio
                                                type={'radio'}
                                                name="due_date"
                                                theme={themeUi}
                                                onChange={() => updateDueDate(selectedDueDate.dueDateType)}
                                                checked={selectedDueDate.selected}
                                                disabled={selectedDueDate.disabled}
                                            />
                                            <DueDateOptionLabelText theme={themeUi}>
                                                {selectedDueDate.label}
                                                <DueDateOptionDateText>
                                                    {selectedDueDate.value}
                                                </DueDateOptionDateText>
                                            </DueDateOptionLabelText>
                                        </DueDateOptionLabel>
                                    );
                                })}
                            </DueDateContentWrapper>
                        )}
                    </FOLGapCalculateContentWrapper> */}
                
                    <strong style={{ fontSize: "14px" }}>Route Load</strong>
                    <div className='chart-wrapper'>
                        <CustomLegend chartOptions={chartoptions} setChartOptions={setChartOptions} />
                        <div className='chart-scroll' style={{ overflowX: chartoptions?.data?.length > 10 ? "scroll" : "hidden" }}>
                            <AgCharts
                                options={chartoptions}
                                style={{ height:"100%", width: chartoptions?.data?.length > 10 ? `${100*chartoptions?.data?.length + "px"}` : "100%"}}
                                />
                        </div>
                    </div>
                </RouteContentWrapper>
            }

            <div style={{ zoom: '0.7', marginTop: '10px' }}>
                <div key={'1'} style={{ display: 'flex', justifyContent: 'right', gap: '8px', borderTop: '2px dashed #A0A0A0', padding: '20px 20px 20px 0' }}>

                    <VFButtonOutline
                        onClick={() => {
                            if (showFOLGapDetails){
                                setShowFOLGapDetails(false) 
                            }
                            else {
                                setShowModal(false)
                            }
                        }}
                        width={ showFOLGapDetails? 160 : 130}
                        themeUi={themeUi} >
                        {showFOLGapDetails ? "No, Go Back" : "Cancel"}
                    </VFButtonOutline>

                    <VFButton
                        onClick={() => {
                            if (!showFOLGapDetails) {  
                                SaveRoute()
                            } else {
                                fetchFolGap();
                                // setShowFOLGapDetails(true)
                            }
                        }}
                        themeUi={themeUi}
                        width={ showFOLGapDetails? 160 : 130}
                        style={{
                            pointerEvents: isSaveDisabled ? "none" : "auto",
                            opacity: isSaveDisabled ? "0.5" : ""
                            }} >
                        {showFOLGapDetails? "Yes, Change Route": "Save Routes"}
                    </VFButton>

                </div>
            </div>
        </VFModalCard>
    )
}

export default React.memo(EditRouteModal);