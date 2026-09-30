import { AgCharts } from 'ag-charts-react'
import React, { useEffect, useMemo, } from 'react'
import { useSaveRouteData } from '../../../../../VectorFlow/Services/MTO/Production/DynamicReleaseManagement'
import VFModalCard from '../../../../../components/VectorFLOW/commons/VFModalCard'
import RouteAssignment from '../../Common/RouteAssignment/RouteAssignment'
import { RouteContentWrapper, Text } from '../../Common/EditRouteModal/styles'
import OverlayLoader from '../../Common/Loader'
import { notifyError, notifySuccess } from '../../../../../helpers/notify'


const EditRouteModal = ({selectedPlant, itemTypeId,chartoptions, dataUpdated, setDataUpdated, setRouteNum, lineCCRDetails, master, setRoute, route, showModal, setShowModal, themeUi, orderKey }: any) => {
    
    const { mutateAsync: saveRouteData, isLoading, isSuccess, isError } = useSaveRouteData();

    type Route = {
        ccrId: number;
        routeId: number;
        ccrGrpId: number;
        ps: number;
    };

    
    useEffect(() => {
        if (isSuccess) {
            notifySuccess("Route updated successfully!")
        }
        if (isError) {
            notifyError("Failed to update route data")
        }
    }, [isSuccess, isError])

    type LineCcr = {
        [order: string]: {
            [ccrId: string]: {
                load: number;
                pcqty: number;
                rid: number;
            };
        };
    };

    function convertToRequiredFormat(routes: Route[], lineCcr: LineCcr): any {

        const myCCRDetails: any = [];

        routes.forEach((e: any, i) => {
            const perCCRDetail = {
                "ccrid": e[1].value,
                "ccrgrp": e[0].value,
                "pcQty": lineCcr[e[1].value]?.pcqty ? lineCcr[e[1].value]?.pcqty : 0,
                "pos": (i + 1).toString(),
                "ol": lineCcr[e[1].value]?.load ? lineCcr[e[1].value]?.load : 0,
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
                        "route": routeName,
                        "ok": orderKey,
                        "ccrdetails": myCCRDetails
                    }
                ]
            }
        }

        return finalData;


    }

    const SaveRoute = async () => {
        const data = convertToRequiredFormat(route, lineCCRDetails);
        try {
            const response = await saveRouteData({body : JSON.parse(JSON.stringify(data)) , update_order_wip : 1})
            if (response.status === 200) {
                setRouteNum('');
                setDataUpdated(!dataUpdated)
                setShowModal(false);
            }
        }
        catch (error) {
            console.log(error)
        }
    }

    useEffect(() => {
        if (isSuccess) {
            setShowModal(false);
        }
    }, [isSuccess])


    
    // const CCRItemTypeMappingMasterLookup = useMemo(() => {
    //     const mappingLookup = new Map<string, Set<string>>();
    //     if (master?.CCRItemTypeMappingMaster) {
    //         master.CCRItemTypeMappingMaster.forEach((mapping: { ccrId: string, it: string }) => {
    //             if (!mappingLookup.has(mapping.ccrId)) {
    //                 mappingLookup.set(mapping.ccrId, new Set());
    //             }
    //             mappingLookup.get(mapping.ccrId)!.add(mapping.it);
    //         });
    //     }
    //     return mappingLookup
    // }, [master?.CCRItemTypeMappingMaster])

    const calculateCCGroups = () => {

        // Get all CCRs that have mappings for the current item type
        const validCCRs = new Set<string>();
        master?.CCRItemTypeMappingMaster?.forEach((mapping: any) => {
            if (mapping.it === itemTypeId) {
                validCCRs.add(mapping.ccrId);
            }
        });

        // Filter CCR groups based on valid CCRs and selected plant
        const filteredCCRGroups = master?.ccrGroups?.map((ccrGroup: any) => {
            // Filter CCRs within each group
            const filteredCCRs = ccrGroup.ccrs.filter((ccr: any) => {
                return ccr.plant_id === selectedPlant && validCCRs.has(ccr.value);
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
    


    const ccrGroups = useMemo(calculateCCGroups, [master ,selectedPlant])

    useEffect(() => {
        if (route && ccrGroups) {
            // Get all valid CCR values from ccrGroups
            const validCCRValues = new Set(
                ccrGroups?.flatMap((group: any) => 
                    group?.ccrs?.map((ccr: any) => ccr?.value)
                )
            );

        }
    }, [ccrGroups]);

    return (
        <VFModalCard openModal={showModal} closeModal={() => { setRouteNum(''), setShowModal((false)) }} headerText={'Edit Route'} headerIcon={''} closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"} paddingLeftAndRight={0} headerTextColor={'black'} backgroundColor={'f4f4f4'} data-testid="vfmultifilter-img" >
            {isLoading && <OverlayLoader message='Saving route data' />}
            <RouteContentWrapper>
                <Text>
                    You can change route by selecting CCR from drop-down
                </Text>
                {
                    master && ccrGroups &&

                    (<RouteAssignment
                        isEditable={true}
                        theme={themeUi}
                        ccrGroupMaster={ccrGroups}
                        selectedRoutes={route}
                        setSelectedRoutes={setRoute}
                    />)
                }
                <strong style={{ fontSize: "14px" }}>Route Load</strong>
                <div style={{ height: "220px" }}>
                    <AgCharts options={chartoptions} />
                </div>
            </RouteContentWrapper>
            <div style={{ zoom: '0.7', marginTop: '10px' }}>
                <div key={'1'} style={{ display: 'flex', justifyContent: 'right', gap: '8px', borderTop: '2px dashed #A0A0A0', padding: '20px 20px 20px 0' }}>

                    <div>
                        <div onClick={() => { setRouteNum(''), setShowModal(false) }} style={{
                            background: 'white', color: 'grey', font: 'normal normal 300 16px/24px Roboto',
                            padding: '10px 20px',
                            fontWeight: '400',
                            borderRadius: '6px',
                            border: '1px solid grey',
                            boxShadow: '0px 6px 25px #00000029'
                        }} >
                            Cancel
                        </div>
                    </div>
                    <div>

                        <div style={{
                            font: 'normal normal 300 16px/24px Roboto',
                            fontWeight: '400',
                            padding: '10px 20px',
                            color: 'white',
                            borderRadius: '6px',
                            background: `${themeUi ? '#820F4C' : '#820F4C'}`,
                            boxShadow: '0px 6px 25px #00000029'

                        }}
                            onClick={() => { SaveRoute() }}
                        >
                            Save Routes
                        </div>
                    </div>
                </div>
            </div>
        </VFModalCard>
    )
}

export default React.memo(EditRouteModal);
