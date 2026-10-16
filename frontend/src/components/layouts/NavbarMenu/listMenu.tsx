const retainedMenu: any[] = [
  {
    id: 1,
    name: "navbar.listMenuParent.userManagement.title",
    img: "/assets/img/nav/icon_manager_users",
    widthIcon: "28px",
    url: "/profile",
    status: false,
    child: [
      {
        name: "navbar.listMenuParent.userManagement.administration",
        img: "/assets/img/nav/arrow_down.svg",
        url: "/profile",
      },
      {
        name: "Login Audit Report",
        img: "/assets/img/nav/arrow_down.svg",
        url: "/login-audit-report",
      },
      // {
      //   name: "navbar.listMenuParent.userManagement.issueLogs",
      //   img: "/assets/img/nav/arrow_down.svg",
      //   url: "",
      // },
    ],
  },
  {
    id: 2,
    name: "navbar.listMenuParent.masterDataManagement.title",
    img: "/assets/img/nav/master_data",
    url:  '/masters-interceptor/control-panel',
    status: false,
    child: [
      {
        name: "navbar.listMenuParent.masterDataManagement.controlPanel",
        img: "/assets/img/nav/arrow_down.svg",
        url: '/masters-interceptor/control-panel',
      },
      {
        name: "navbar.listMenuParent.masterDataManagement.savedDrafts",
        img: "/assets/img/nav/arrow_down.svg",
        url: "/masters-interceptor/saved-drafts",
      },
      {
        name: "navbar.listMenuParent.masterDataManagement.taskPendingForReview",
        img: "/assets/img/nav/arrow_down.svg",
        url: "/masters-interceptor/task-pending",
      },
      {
        name: "navbar.listMenuParent.masterDataManagement.taskStatus",
        img: "/assets/img/nav/arrow_down.svg",
        url: "/masters-interceptor/task-status",
      },
      {
        name: "navbar.listMenuParent.masterDataManagement.modificationHistory",
        img: "/assets/img/nav/arrow_down.svg",
        url: "/masters-interceptor/data-modification-history",
      }
    ],
  },
  // {
  //   id: 3,
  //   name: "navbar.listMenuParent.dynamicGridControl_AssortmentPlanning.title",
  //   img: "/assets/img/nav/dynamic_assortment",
  //   url: "",
  //   status: false,
  //   child: [
  //     {
  //       name: "navbar.listMenuParent.dynamicGridControl_AssortmentPlanning.gridSizing",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //     {
  //       name: "navbar.listMenuParent.dynamicGridControl_AssortmentPlanning.productGridMapping",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //     {
  //       name: "navbar.listMenuParent.dynamicGridControl_AssortmentPlanning.currentStoreWiseAssortment",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //     {
  //       name: "navbar.listMenuParent.dynamicGridControl_AssortmentPlanning.newStoreAssortment",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //   ],
  // },
  // {
  //   id: 4,
  //   name: "navbar.listMenuParent.replenishment_replacement.title",
  //   img: "/assets/img/nav/replenishment_replacement",
  //   url: "",
  //   status: false,
  //   child: [
  //     {
  //       name: "navbar.listMenuParent.replenishment_replacement.bufferPenetrationReport",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //     {
  //       name: "navbar.listMenuParent.replenishment_replacement.bufferTrendReport",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //     {
  //       name: "navbar.listMenuParent.replenishment_replacement.bufferTrendGraph",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //     {
  //       name: "navbar.listMenuParent.replenishment_replacement.rationedRequirementReport",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //     {
  //       name: "navbar.listMenuParent.replenishment_replacement.supplierDispatchReport",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //     {
  //       name: "navbar.listMenuParent.replenishment_replacement.buyerOrderReport",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //     {
  //       name: "navbar.listMenuParent.replenishment_replacement.vendorDispatchReport",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //     {
  //       name: "navbar.listMenuParent.replenishment_replacement.availabilityComparison",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //   ],
  // },
  // {
  //   id: 5,
  //   name: "navbar.listMenuParent.groupLifeCycleManagement.title",
  //   img: "/assets/img/nav/grouplifecycle",
  //   widthIcon: "28px",
  //   url: "",
  //   status: false,
  //   child: [
  //     {
  //       name: "navbar.listMenuParent.groupLifeCycleManagement.item1",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //     {
  //       name: "navbar.listMenuParent.groupLifeCycleManagement.item2",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //     {
  //       name: "navbar.listMenuParent.groupLifeCycleManagement.item3",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //     {
  //       name: "navbar.listMenuParent.groupLifeCycleManagement.item4",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //   ],
  // },
  {
    id: 6,
    name: "navbar.listMenuParent.innerStoreTransfers.title",
    img: "/assets/img/nav/IST",
    url: "/ist-requests",
    status: false,
    lp_attr : true,
    lp_img : "/assets/img/IST 1.svg",
    rp_img : "/assets/img/IST 2.svg",
    app_id : 1,
    child: [
      {
        name: "navbar.listMenuParent.innerStoreTransfers.manualUpload",
        img: "/assets/img/nav/arrow_down.svg",
        url: "/manual-upload",
      },
      {
        name: "navbar.listMenuParent.innerStoreTransfers.pendingISTRequests",
        img: "/assets/img/nav/arrow_down.svg",
        url: "/ist-requests",
      },
      {
        name: "navbar.listMenuParent.innerStoreTransfers.ISTStatus",
        img: "/assets/img/nav/arrow_down.svg",
        url: "/ist-status",
      },
      {
        name: "navbar.listMenuParent.innerStoreTransfers.ISTForcedClosure",
        img: "/assets/img/nav/arrow_down.svg",
        url: "/ist-forced-closure",
      },
      {
        name: "navbar.listMenuParent.innerStoreTransfers.storeStatus",
        img: "/assets/img/nav/arrow_down.svg",
        url: "/store-status",
      },
      {
        name: "navbar.listMenuParent.innerStoreTransfers.availabilityComparison",
        img: "/assets/img/nav/arrow_down.svg",
        url: "/availability-comparison",
      },
    ],
  },
  {
    id: 9,
    name: "Replenishment and Replacement",
    img: "/assets/img/VectorFLOW/BPR/replacement",
    url: "/mta/supply-chain-intelligence-hub/planning",
    status: false,
    lp_img : "/assets/img/Replacement.svg",
    app_id : 2,
    avoidHeader: true,
    child: [
      {
        name: "Supply Chain Intelligence Hub",
        img: "/assets/img/nav/arrow_down.svg",
        url: "/supply-chain-intelligence-hub",
        child: [
          {
            name: "Planning",
            lp_attr : true,
            img: "/assets/img/nav/arrow_down.svg",
            lp_img : "/assets/img/planning.svg",
            rp_img : "/assets/img/planning1.svg",
            url: "/mta/supply-chain-intelligence-hub/planning",
          },
          {
            name: "BPR",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mta/supply-chain-intelligence-hub/bpr",
          },
          // {
          //   name: "Dispatch Planning",
          //   img: "/assets/img/nav/arrow_down.svg",
          //   url: "/supply-chain-intelligence-hub/dispatch-planning",
          // },
          {
            name: "Open Expediting Requests",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mta/supply-chain-intelligence-hub/open-expediting-requests",
          },
 
          // {
          //   name: "Vendor Dispatch Report",
          //   img: "/assets/img/nav/arrow_down.svg",
          //   url: "//supply-chain-intelligence-hub/vendor-dispatch-report",
          // },
          {
            name: "Rationed Requirement Report",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mta/supply-chain-intelligence-hub/rrr",
 
          },
          {
            name: "Rationed Requirement Report - Color Bandwise",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mta/supply-chain-intelligence-hub/rrr-color-bandwise",
          },
          {
            name: "Buyer Order Report",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mta/supply-chain-intelligence-hub/bor",
 
          },
          {
            name: "Buyer Order Report - Color Bandwise",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mta/supply-chain-intelligence-hub/bor-color-bandwise",
 
          },
          {
            name: "Supplier Wise Allocation Report",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mta/supply-chain-intelligence-hub/SupplierWiseAllocation",
 
          },
          {
            name: "Order Allocation Report",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mta/supply-chain-intelligence-hub/order-allocation-report",
 
          },
          {
            name: "Total Requirement Report",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mta/supply-chain-intelligence-hub/total-requirement-report",
 
          },
          {
            name: "Supplier Dispatch Report",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mta/supply-chain-intelligence-hub/sdr",
 
          },
          {
            name: "Elephant Order",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mta/supply-chain-intelligence-hub/eo",
 
          },
          {
            name: "Merchandising Grid",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/supply-chain-intelligence-hub/merchandising-grid",
          },
        ]
      },
      {
        name: "Logistics",
        img: "/assets/img/nav/arrow_down.svg",
        url: "/logistics",
 
        child: [
          {
            name: "InTransit Whereabouts",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mta/logistics/intransit-whereabouts",
 
          }
        ]
      },
      {
        name: "Insights & Trends",
        img: "/assets/img/nav/arrow_down.svg",
        url: "/insights-and-trends",
        child: [
          {
            name: "Buffer Trend Report (BTR)",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mta/insights-and-trends/buffer-trend-report",
          },
          {
            name: "Buffer Trends",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mta/insights-and-trends/buffer-trends",
          },
          // {
          //   name: "Logistics Insights",
          //   img: "/assets/img/nav/arrow_down.svg",
          //   url: "/insights-and-trends/logistics-insights",
          // },
          {
            name: "Guided Insights",
            img: "/assets/img/nav/arrow_down.svg",
            lp_attr : true,
            url: "/mta/insights-and-trends/guided-insights",
            lp_img : "/assets/img/Guided-In.svg",
            rp_img : "/assets/img/Guided-In1.svg",
          },
          {
            name: "Research Insights",
            img: "/assets/img/nav/arrow_down.svg",
            lp_attr : true,
            url: "/mta/insights-and-trends/research-insights",
            lp_img : "/assets/img/Reasearch-in.svg",
            rp_img : "/assets/img/Reasearch-in1.svg",
          }
        ]
      },
      {
        name: "DBM",
        img: "/assets/img/nav/arrow_down.svg",
        url: "/dbm",
        child: [
          {
            name: "DBM Norm Suggestions",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mta/dbm/dbm-norm-suggestions",
          }
        ]
      }
    ],
  },
 
  // {
  //   id: 7,
  //   name: "navbar.listMenuParent.velocityAnalysis.title",
  //   img: "/assets/img/nav/velocity_analysis",
  //   url: "/",
  //   status: false,
  //   child: [
  //     {
  //       name: "navbar.listMenuParent.velocityAnalysis.earlyIdentificationOfLaggards",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //     {
  //       name: "navbar.listMenuParent.velocityAnalysis.itr",
  //       img: "/assets/img/nav/arrow_down.svg",
  //       url: "",
  //     },
  //   ],
  // },
  

  {
    id: 19,
    name: "Procurement",
    img: "/assets/img/nav/procurement",
    lp_attr : true,
    app_id : 3,
    url: "/mto/procurement/material-coverage-open-sales",
    lp_img : "/assets/img/Prourment.svg",
    rp_img : "/assets/img/Prourment1.svg",
    status: false,
    avoidHeader: true,
    child: [
      {
        name: "Procurement",
        img: "/assets/img/nav/procurement",
        url: "/mto/procurement/material-coverage-open-sales",
        child: [
          {
            name: "Material Coverage For Open Sales",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/procurement/material-coverage-open-sales",
          },
          {
            name: "Procurement Planning",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/procurement-planning/planning",
          },
          {
            name: "Material Requirement",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/procurement/material-requirement",
          },
        ]
      },
      {
        name: "Insight and Trends",
        img: "/assets/img/nav/arrow_down.svg",
        url: "/mto/procurement/insights-and-trends",
        child: [
          {
            name: "Day Wise Coverage",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/procurement/insights-and-trends/day-wise-coverage",
          },
          {
            name: "RM/PM Orderwise Coverage",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/procurement/insights-and-trends/rmpm-orderwise-coverage",
          },
          {
            name: "RM/PM Buffer Trend",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/procurement/insights-and-trends/rmpm-buffer-trends",
          },
          {
            name: "Expediting RM/Suppliers",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/procurement/insights-and-trends/rmpm-expediting-rm-suppliers",
          }
        ]

      },
    ],
  },
  {
    id: 10,
    name: "navbar.listMenuParent.prodAndPlanningScheduling.title",
    img: "/assets/img/nav/prod-plan-icon",
    lp_attr : true,
    app_id : 3,
    lp_img : "/assets/img/Prod-icon.svg",
    rp_img : "/assets/img/Prod-icon1.svg",
    url: "/mto/production-planning-scheduling/enquiry-response",
    status: false,
    avoidHeader: true,
    child: [
      {
        name: "navbar.listMenuParent.prodAndPlanningScheduling.title",
        img: "/assets/img/nav/prod-plan-icon",
        url: "/mto/production-planning-scheduling/enquiry-response", 
        child: [
          {
            name: "navbar.listMenuParent.prodAndPlanningScheduling.enquiryResponse",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/production-planning-scheduling/enquiry-response",
          },
          {
            name: "navbar.listMenuParent.prodAndPlanningScheduling.dueDateQuotation",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/production-planning-and-scheduling/due-date-quotation",
          },
          {
            name: "navbar.listMenuParent.prodAndPlanningScheduling.orderRescheduling",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/production-planning-and-scheduling/order-rescheduling",
          },
          {
            name: "navbar.listMenuParent.prodAndPlanningScheduling.fullKitAssignment",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/production-planning-scheduling/full-kit-assignment",
          },
          {
            name: "navbar.listMenuParent.prodAndPlanningScheduling.dynamicReleaseManagement",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/production-planning-scheduling/dynamic-release-mangement",
          },
          {
            name: "navbar.listMenuParent.prodAndPlanningScheduling.deptWiseBMReport",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/production-planning-scheduling/deptwise-bm-report",
          },
          {
            name: "navbar.listMenuParent.prodAndPlanningScheduling.overallBMReport",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/production-planning-scheduling/overall-bm-report",
          },
        ]
      },
      {
        name: "navbar.listMenuParent.prodAndPlanningScheduling.Scheduling",
        img: "/assets/img/nav/arrow_down.svg",
        url: "",
        child: [
          {
            name: "Scheduling",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/production/scheduling",
          },
        ]
      },
      {
        name: "navbar.listMenuParent.prodAndPlanningScheduling.insightAndTrends",
        img: "/assets/img/nav/arrow_down.svg",
        url: "",
        child: [
          {
            name: "BM Trends",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/production-planning-scheduling/insight-and-trends/bm-trends",
          },
          {
            name: "Future Order Load",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/production-planning-scheduling/insight-and-trends/future-order-load-chart',
          },
          {
            name: "FOL Summary",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/production-planning-scheduling/insights-and-trends/fol-summary",
          },
          {
            name: "STPL & Full Kits",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/production-planning-scheduling/insight-and-trends/stpl-full-kits",
          },
          {
            name: "Elapsed Time",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/production-planning-scheduling/insights-and-trends/elapsed-time',
          },
          {
            name: "Orders At Risk",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/production-planning-scheduling/insight-and-trends/order-at-risk",
          },
          {
            name: "Order Balance",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/production-planning-scheduling/insight-and-trends/order-balance",
          },

        ]
      },
    ],
  },
  {
    id: 8,
    name: "navbar.listMenuParent.miscellaneousReports.title",
    img: "/assets/img/nav/miscellaneousReports",
    url: "",
    status: false,
    child: [
      // {
      //   name: "navbar.listMenuParent.miscellaneousReports.bufferPenetrationReport",
      //   img: "/assets/img/nav/arrow_down.svg",
      //   imgHover: "/assets/img/nav/DownloadReport-Icon.svg",
      //   url: "/api/download-reports/bpr",
      // },
      // {
      //   name: "navbar.listMenuParent.miscellaneousReports.fashionRationedRequirement",
      //   img: "/assets/img/nav/arrow_down.svg",
      //   imgHover: "/assets/img/nav/DownloadReport-Icon.svg",
      //   url: "/api/download-reports/fr",
      // },
      // {
      //   name: "navbar.listMenuParent.miscellaneousReports.rosn",
      //   img: "/assets/img/nav/arrow_down.svg",
      //   imgHover: "/assets/img/nav/DownloadReport-Icon.svg",
      //   url: "/api/download-reports/rosn",
      // },
      // {
      //   name: "navbar.listMenuParent.miscellaneousReports.store_classification",
      //   img: "/assets/img/nav/arrow_down.svg",
      //   imgHover: "/assets/img/nav/DownloadReport-Icon.svg",
      //   url: "/api/download-reports/store_classification",
      // },
      // {
      //   name: "navbar.listMenuParent.miscellaneousReports.ist",
      //   img: "/assets/img/nav/arrow_down.svg",
      //   imgHover: "/assets/img/nav/DownloadReport-Icon.svg",
      //   url: "/api/download-reports/ist",
      // },
      // {
      //   name: "navbar.listMenuParent.miscellaneousReports.dailyDataUnavailibilityReport",
      //   img: "/assets/img/nav/arrow_down.svg",
      //   imgHover: "/assets/img/nav/DownloadReport-Icon.svg",
      //   url: "",
      // },
      // {
      //   name: "navbar.listMenuParent.miscellaneousReports.invalidDataReport",
      //   img: "/assets/img/nav/arrow_down.svg",
      //   imgHover: "/assets/img/nav/DownloadReport-Icon.svg",
      //   url: "",
      // },
      // {
      //   name: "navbar.listMenuParent.miscellaneousReports.uiUploadLogs_AddNewSKULoc",
      //   img: "/assets/img/nav/arrow_down.svg",
      //   imgHover: "/assets/img/nav/DownloadReport-Icon.svg",
      //   url: "",
      // },
      // {
      //   name: "navbar.listMenuParent.miscellaneousReports.uiUploadLogs_ModifySKULoc",
      //   img: "/assets/img/nav/arrow_down.svg",
      //   imgHover: "/assets/img/nav/DownloadReport-Icon.svg",
      //   url: "",
      // },
      // {
      //   name: "navbar.listMenuParent.miscellaneousReports.uiUploadLogs_RemoveSKULoc",
      //   img: "/assets/img/nav/arrow_down.svg",
      //   imgHover: "/assets/img/nav/DownloadReport-Icon.svg",
      //   url: "",
      // },
      // {
      //   name: "navbar.listMenuParent.miscellaneousReports.uiUploadLogs_SKUMaster",
      //   img: "/assets/img/nav/arrow_down.svg",
      //   imgHover: "/assets/img/nav/DownloadReport-Icon.svg",
      //   url: "",
      // },
    ],
  },
  {
    id: 11,
    name: "navbar.listMenuParent.poogi.title",
    img: "/assets/img/nav/poogi-module1",
    lp_attr : true ,
    app_id : 3,
    lp_img :"/assets/img/Poogi 3.svg",
    rp_img :"/assets/img/Poogi 4.svg",
    url: "/mto/poogi/reasons-for-delayed-orders",
    status: false,
    avoidHeader: true,
    child: [
      {
        name: "navbar.listMenuParent.poogi.title",
        img: "/assets/img/nav/poogi-module1",
        url: "/mto/poogi/reasons-for-delayed-orders",
        child: [
          {
            name: "navbar.listMenuParent.poogi.reasonForDelayedOrders",
            img: "/assets/img/nav/arrow_down.svg",
            url: "/mto/poogi/reasons-for-delayed-orders",
          },
        ]
      },
      {
        name: "navbar.listMenuParent.poogi.insightAndTrends",
        img: "/assets/img/nav/arrow_down.svg",
        url: "",
        child: [
          {
            name: "Resource Utilization & WIP Profile",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/poogi/insight-and-trends/resource-utilization-wip-profile',
          },
          {
            name: "OTIF Analysis",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/poogi/insight-and-trends/otif-analysis',
          },
          {
            name: "OT & IF Analysis",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/poogi/insight-and-trends/ot-and-if-analysis',
          },
          {
            name: "Lead Time",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/poogi/insight-and-trends/lead-time',
          },
          {
            name: "Top Failure Reasons",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/poogi/insight-and-trends/top-failure-reasons',
          },
          {
            name: "Trend Of Failure Reasons",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/poogi/insight-and-trends/trend-of-failure-reason',
          },
        ]
      },
    ],
  },
  {
    id: 12,
    name: "navbar.listMenuParent.manufacturingHub.title",
    img: "/assets/img/nav/machine2",
    lp_attr : true , 
    app_id : 3,
    avoidHeader: true,
    lp_img : "/assets/img/Manufacturing.svg",
    rp_img : "/assets/img/Manufacturing1.svg",
    url: "/mto/manufacturing-intelligence-hub/delivery-performance/bm-trends",
    status: false,
    child: [
      {
        name: "navbar.listMenuParent.manufacturingHub.deliveryPerformance",
        img: "/assets/img/nav/arrow_down.svg",
        url: "",
        child: [
          {
            name: "navbar.listMenuParent.manufacturingHub.bmtrends",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/manufacturing-intelligence-hub/delivery-performance/bm-trends',
          },
          {
            name: "navbar.listMenuParent.manufacturingHub.otifanalysis",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/manufacturing-intelligence-hub/delivery-performance/otif-analysis',
          },
          {
            name: "navbar.listMenuParent.manufacturingHub.otandifanalysis",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/manufacturing-intelligence-hub/delivery-performance/ot-and-if-analysis',
          },
          {
            name: "navbar.listMenuParent.manufacturingHub.leadtime",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/manufacturing-intelligence-hub/delivery-performance/lead-time',
          },

        ],

      },
      {
        name: "navbar.listMenuParent.manufacturingHub.congestionanalysis",
        img: "/assets/img/nav/arrow_down.svg",
        url: "",
        child: [
          {
            name: "navbar.listMenuParent.manufacturingHub.elapsedtime",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/manufacturing-intelligence-hub/congestion-analysis/elapsed-time',
          },
          {
            name: "navbar.listMenuParent.manufacturingHub.orderatrisk",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/manufacturing-intelligence-hub/congestion-analysis/orders-at-risk',
          },
          {
            name: "navbar.listMenuParent.manufacturingHub.orderbalance",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/manufacturing-intelligence-hub/congestion-analysis/order-balance',
          },
        ]
      },
      {
        name: "navbar.listMenuParent.manufacturingHub.forwardexecution",
        img: "/assets/img/nav/arrow_down.svg",
        url: "",
        child: [
          {
            name: "navbar.listMenuParent.manufacturingHub.folsummary",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/manufacturing-intelligence-hub/forward-exceution/fol-summary',
          },
          {
            name: "navbar.listMenuParent.manufacturingHub.STPL&FullKits",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/manufacturing-intelligence-hub/forward-exceution/stpl-and-fullkit',
          },
          {
            name: "navbar.listMenuParent.manufacturingHub.daywisecoverage",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/manufacturing-intelligence-hub/forward-exceution/day-wise-coverage',
          },
          {
            name: "navbar.listMenuParent.manufacturingHub.rmpmorderwisecoverage",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-order-wise-coverage',
          },
          {
            name: "navbar.listMenuParent.manufacturingHub.expeditingrm",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/manufacturing-intelligence-hub/forward-exceution/expetiting-rm-supplier',
          },
          {
            name: "navbar.listMenuParent.manufacturingHub.rmpmbuffertrend",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-buffer-trend',
          },
        ]
      },
      {
        name: "navbar.listMenuParent.manufacturingHub.improvementaread",
        img: "/assets/img/nav/arrow_down.svg",
        url: "",
        child: [
          {
            name: "navbar.listMenuParent.manufacturingHub.topfailurereason",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/manufacturing-intelligence-hub/improvement-areas/top-failure-reasons',
          },
          {
            name: "navbar.listMenuParent.manufacturingHub.trenfailurereason",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/manufacturing-intelligence-hub/improvement-areas/trends-failure-reasons',
          },
          {
            name: "navbar.listMenuParent.manufacturingHub.resourceutilizationwip",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/manufacturing-intelligence-hub/improvement-areas/resource-wip-profile',
          },
        ]
      },
      {
        name: "navbar.listMenuParent.manufacturingHub.futureorderloadchart",
        img: "/assets/img/nav/arrow_down.svg",
        url: "",
        child: [
          {
            name: "navbar.listMenuParent.manufacturingHub.futureorderloadchart",
            img: "/assets/img/nav/arrow_down.svg",
            url: '/mto/manufacturing-intelligence-hub/future-order-load-chart',
          }
        ]
      }
    ],
  },
  // {
  //   id: 111,
  //   name: "Scheduling",
  //   img: "/assets/img/nav/poogi-module1",
  //   lp_attr : true ,
  //   app_id : 3,
  //   lp_img :"/assets/img/Poogi 3.svg",
  //   rp_img :"/assets/img/Poogi 4.svg",
  //   url: "/scheduling",
  //   status: false,
  //   avoidHeader: true,
  //   child: [
  //     {
  //       name: "Scheduling",
  //       img: "/assets/img/nav/poogi-module1",
  //       url: "/scheduling",
  //       child: [
  //         {
  //           name: "Scheduling",
  //           img: "/assets/img/nav/arrow_down.svg",
  //           url: "/scheduling",
  //         },
  //       ]
  //     }
  //   ],
  // },

];

// The demo deliberately exposes only source-backed MTA surfaces.  Routes are
// retained in the application for the full product, but must not imply that a
// synthetic demonstration supports a known unresolved producer or workflow.
const demoUnavailableRoutes = new Set([
  "/mta/supply-chain-intelligence-hub/open-expediting-requests",
  "/mta/supply-chain-intelligence-hub/order-allocation-report",
  "/mta/supply-chain-intelligence-hub/total-requirement-report",
  "/mta/supply-chain-intelligence-hub/eo",
  "/supply-chain-intelligence-hub/merchandising-grid",
]);

const withoutDemoGaps = (items: any[]): any[] => items
  .filter((item) => !demoUnavailableRoutes.has(item.url))
  .map((item) => item.child ? { ...item, child: withoutDemoGaps(item.child) } : item)
  .filter((item) => !item.child || item.child.length > 0);

export const listMenuParent: any = process.env.REACT_APP_DEMO_MODE === "true"
  ? withoutDemoGaps(retainedMenu)
  : retainedMenu;



