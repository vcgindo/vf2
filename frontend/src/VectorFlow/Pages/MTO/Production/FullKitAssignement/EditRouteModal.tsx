import React, { useEffect, useMemo, useState } from 'react'
import { AgCharts } from 'ag-charts-react'
import { useGetLineCCRDetails, useGetRouteDetails } from '../../../../../VectorFlow/Services/MTO/Production/DueDateQuotation'
import VFModalCard from '../../../../../components/VectorFLOW/commons/VFModalCard'
import RouteAssignment from '../../Common/RouteAssignment/RouteAssignment'
import { RouteContentWrapper, Text } from '../../Common/EditRouteModal/styles'
import { Rectangle } from './RectangleMarker'
import { notifyError } from '../../../../../helpers/notify'
import _ from 'lodash'
import { useSaveRouteData } from '../../../../../VectorFlow/Services/MTO/Production/DynamicReleaseManagement'
import VFButton from '../../../../../components/VectorFLOW/commons/VFButton'
import VFButtonOutline from '../../../../../components/VectorFLOW/commons/VFButtonOutline'

type LineCcr = {
    [order: string]: {
        [ccrId: string]: {
            load: number;
            pcqty: number;
            rid: number;
        };
    };
};

type Route = {
    ccrId: number;
    routeId: number;
    ccrGrpId: number;
    ps: number;
};

const EditRouteModal = ({ showModal, setShowModal, graphData, theme, master, routeId, plantId, orderKey, setOrderKey, loadDataParams, setLoadDataParams, itemTypeId }: any) => {

    const chartoptions: any = {
        data: graphData,
        series: [
            {
                type: 'bar',
                xKey: 'ccr_name',
                yKey: "stpl_in_days",
                stacked: true,
                strokeWidth: 0,
                fill: "#191919",
                // formatter: (params) => {
                //   return {
                //     fillOpacity: params.datum.selected ? 1 : 0.5,
                //     fill: params.datum.selected ? params.fill : "#191919"
                //   }
                // }
            },
            {
                type: 'bar',
                xKey: 'ccr_name',
                yKey: "allowed_full_kits",
                stacked: true,
                strokeWidth: 0,
                fill: "#EBBF2C",
                // formatter: (params) => {
                //   return {
                //     fill: params.datum.selected ? params.fill : "#A8A8A8"
                //   }
                // },
                // label: {
                //   enabled: true,
                //   formatter: (params: any) => {
                //     return params.datum.groupName
                //   },
                //   placement: "outside",
                //   color: "black",

                // }
            },
            {
                type: 'scatter',
                xKey: 'ccr_name',
                yKey: 'cumulative_wip_limit',
                marker: {
                    size: 10,
                    fill: '#E53F3F',
                    shape: Rectangle,
                    strokeWidth: 0
                },

            },
        ],
        axes: [
            {
                type: 'category',
                position: 'bottom',
                gridLine: {
                    enabled: false
                }
            },
            {
                type: 'number',
                position: 'left',
                title: {
                    text: "Days"
                },
                gridLine: {
                    enabled: false
                }
            },

        ],
        legend: {
            position: "top",
            item: {
                label: {
                    formatter: (props: any) => {
                        if (props.value === "stpl_in_days") {
                            return "Released WIP in Days"

                        }
                        else if (props.value === 'allowed_full_kits') {
                            return 'Allocated Full Kits'
                        }
                        else {
                            return 'Cummulative WIP Limit'
                        }
                    }
                },
                showSeriesStroke: true,
                marker: {
                    size: 15,
                    strokeWidth: 0,
                    shape: 'square', // 'circle', 'square', 'cross', 'plus', 'triangle'
                },
            },
        },

    }

    const { mutateAsync: getRouteDetails, } = useGetRouteDetails();
    const { mutateAsync: getLineCCRDetails, } = useGetLineCCRDetails();
    const { mutateAsync: saveRouteData, } = useSaveRouteData();

    const [selectedRoute, setSelectedRoute] = useState<any>([])
    const [lineCCR, setLineCCR] = useState<any>();

    useEffect(() => {
        getRoute(routeId).then((newRoute) => {
            setSelectedRoute(newRoute);
        })
        if (orderKey)
            getLineCCRData(orderKey)
    }, [routeId, orderKey]);

    const ccrGroupsForPlant = useMemo(() => {
        // Get all CCRs that have mappings for the current item type
        const validCCRs = new Set<string>();
        master?.CCRItemTypeMappingMaster?.forEach((mapping: any) => {
            if (mapping.it === itemTypeId) {
                validCCRs.add(mapping.ccrId);
            }
        });
        
        if (plantId && master?.ccrGroups) {
            return master?.ccrGroups.map((ccrGroup: any) => {
                return {
                    ...ccrGroup, ccrs: ccrGroup.ccrs.filter((ccr: any) => {
                        return ccr.plant_id == plantId && validCCRs.has(ccr.value);
                    })
                }
            })?.filter((ccrGroup: any) => ccrGroup.ccrs.length != 0)
        }
        else {
            return []
        }
    }, [master?.ccrGroups, plantId])


    const getRoute = async (route: any) => {
        try {
            if (typeof route === "number") {
                const data = await getRouteDetails(route);
                const routeDetails = data.data.data;
                routeDetails.sort((a: any, b: any) => a.ps - b.ps)
                const newRoute: any = []
                routeDetails.forEach((routeDetail: any) => {
                    const obj = []
                    const ccrGroup = master?.ccrGroups.find((ccr: any) => ccr.value === routeDetail.ccrGrpId);
                    obj[0] = ccrGroup;
                    obj[1] = ccrGroup.ccrs.find((ccr: any) => ccr.value === routeDetail.ccrId)
                    newRoute[routeDetail.ps - 1] = obj
                })
                return _.cloneDeep(newRoute)
            }
            return []
        }
        catch (err) {
            console.error(err);
            notifyError("Something Went Wrong!");
        }
    }

    const getLineCCRData = async (orderKey: any) => {
        try {
            const data: any = await getLineCCRDetails([orderKey]);
            setLineCCR(data?.data?.data)
        }
        catch (err) {
            notifyError("Something went wrong!")
        }
    }

    const SaveRoute = async () => {
        const data = convertToRequiredFormat(selectedRoute, lineCCR);
        try {
            const response = await saveRouteData({body : JSON.parse(JSON.stringify(data)), update_order_wip : 1})
            if (response.status === 200) {
                setShowModal(false);
                setLoadDataParams({ ...loadDataParams, load_graph_data: true })
            }
        }
        catch (error) {
            console.log(error)
        }
    }


    function convertToRequiredFormat(routes: Route[], lineCcr: LineCcr[]): any {

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
                        "ok": Object.keys(lineCCR)[0],
                        "ccrdetails": myCCRDetails
                    }
                ]
            }
        }

        return finalData;


    }

    return (
        <VFModalCard openModal={showModal} closeModal={() => { setOrderKey(null); setShowModal((false)); setSelectedRoute([]) }} headerText={'Edit Route'} headerIcon={''} closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"} paddingLeftAndRight={0} headerTextColor={'black'} backgroundColor={'f4f4f4'} data-testid="vfmultifilter-img" >
            <RouteContentWrapper>
                <Text>
                    You can change route by selecting CCR from drop-down
                </Text>
                {
                    master && ccrGroupsForPlant &&
                    (<RouteAssignment
                        theme={theme}
                        ccrGroupMaster={ccrGroupsForPlant}
                        selectedRoutes={selectedRoute}
                        setSelectedRoutes={setSelectedRoute}
                    />)
                }
                {/* <RouteAssignment theme={theme} /> */}
                <strong style={{ fontSize: "14px" }}>Route Load</strong>
                <div style={{ height: "300px" }}>
                    <AgCharts options={chartoptions} />
                </div>
            </RouteContentWrapper>
                <div style={{ display: "flex", justifyContent: "end", gap: "1rem",borderTop: '2px dashed #A0A0A0', padding: '20px 20px 20px 0' }}>
                    <VFButtonOutline
                        style={{
                            height: "30px",
                            minWidth: "80px",
                            display: "flex",
                            justifyContent: "center",
                            alignItems: "center",
                            padding: "1rem",
                            fontSize: "14px",
                        }}
                        themeUi={theme}
                        onClick={() => { setOrderKey(null); setShowModal((false)); setSelectedRoute([]); setLineCCR(null); }}>
                        Cancel
                    </VFButtonOutline>
                    <VFButton style={{
                        height: "30px",
                        minWidth: "80px",
                        display: "flex",
                        justifyContent: "center",
                        alignItems: "center",
                        padding: "1rem",
                        fontSize: "14px",
                        boxShadow: "unset"
                    }} themeUi={theme} onClick={() => { SaveRoute() }}>Save Route</VFButton>
                </div>
        </VFModalCard>
    )
}

export default React.memo(EditRouteModal)
