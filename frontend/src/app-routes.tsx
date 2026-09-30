import React, { Suspense, useEffect, useRef } from 'react'
import { useLocation, type RouteObject } from 'react-router-dom'
import { AppLayout } from './components'
import { getStoreTransferModuleRoutes } from './module-store-transfer/app-routes-store-transfer'
import Login from './module-main/pages/auth/login'
// import Home from './module-main/pages/home'
import ManualUpload from './module-store-transfer/pages/manual-upload'
import IstForced from './module-store-transfer/pages/ist-forced'
import StoreStatus from './module-store-transfer/pages/store-status'
import ForgotPassword from './module-main/pages/auth/forgot-password'
import ChangePassword from './module-main/pages/auth/change-password'
import Availability from './module-store-transfer/pages/availability-comparison'
import IstStatus from './module-store-transfer/pages/ist-status/index'
import Profile from './module-store-transfer/pages/profile'
import PageForbidden from './module-store-transfer/pages/forbidden'
import PageNotFound from './module-store-transfer/pages/notFound'
import { useTranslation } from 'react-i18next'
import ControlPanel from './VectorFlow/Pages/MTA/MDM/ControlPanel'
import ViewModify from './VectorFlow/Pages/MTA/MDM/ViewModify'
import AddRecord from './VectorFlow/Pages/MTA/MDM/AddRecord'
import DeleteRecord from './VectorFlow/Pages/MTA/MDM/DeleteRecord'
import SavedDrafts from './VectorFlow/Pages/MTA/MDM/SavedDrafts'
import TaskStatus from './VectorFlow/Pages/MTA/MDM/TaskStatus'
import TaskPendingForReview from './VectorFlow/Pages/MTA/MDM/TaskPendingForReview'
import BuyerOrderReport from './VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/BuyerOrderReport'
import Planning from './VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/Planning'
import ResearchInsights from './VectorFlow/Pages/MTA/InsightsAndTrends/ResearchInsights'
import BPR from './VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/BPR'
import RRR from './VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/RationedRequirementReport'
import GuidedInsights from './VectorFlow/Pages/MTA/InsightsAndTrends/GuidedInsights'
import BufferTrends from './VectorFlow/Pages/MTA/InsightsAndTrends/BufferTrends'
import BufferTrendReport from './VectorFlow/Pages/MTA/InsightsAndTrends/BTR'
import DBM from './VectorFlow/Pages/MTA/DBM/DBMNormSuggestions'
import EnquiryResponse from './VectorFlow/Pages/MTO/Production/EnquiryResponse'
import OpenExpeditingRequests from './VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/OpenExpeditingRequests'
import MaterialCov from './VectorFlow/Pages/MTO/Procurement/MaterialCoverage/MaterialCov'
import ProcurementPlanning from './VectorFlow/Pages/MTO/Procurement/Planning';
import SimulateFullKit from './VectorFlow/Pages/MTO/Procurement/Planning/SimulateFullKit';
import InTransitWhereAbouts from './VectorFlow/Pages/MTA/Logistics/InTransitWhereAbouts'
import DayWiseCoverage from './VectorFlow/Pages/MTO/Procurement/InsightsAndTrends/DayWiseCoverage'
import MaterialRequirement from './VectorFlow/Pages/MTO/Procurement/MaterialRequirement/MaterialRequirement'
import RMPMBufferTrends from './VectorFlow/Pages/MTO/Procurement/InsightsAndTrends/RMPMBufferTrends'
import RMPMOrderwiseCoverage from './VectorFlow/Pages/MTO/Procurement/InsightsAndTrends/RMPMOrderwiseCoverage'
import DptWiseBMReport from './VectorFlow/Pages/MTO/Production/DepartmentWiseBMReport/index';
import FullKitAssignment from './VectorFlow/Pages/MTO/Production/FullKitAssignement'
import OrderRescheduling from './VectorFlow/Pages/MTO/Production/OrderRescheduling'
import RMExpeditionSuppliers from './VectorFlow/Pages/MTO/Procurement/InsightsAndTrends/RMPMExpediting/index'
import BMTrends from './VectorFlow/Pages/MTO/Production/InsightsAndTrends/BMTrends'
import SupplierDispatchReport from './VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/SupplierDispatchReport'
import DataModificationHistory from './VectorFlow/Pages/MTA/MDM/DataModificationHistory'
import MCGrid from './VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/MerchandisingGrid'
import STPLAndFullKits from './VectorFlow/Pages/MTO/Production/InsightsAndTrends/STPLAndFullKits'
import OrderAtRisk from './VectorFlow/Pages/MTO/Production/InsightsAndTrends/OrderAtRisk'
import DueDateQuotation from './VectorFlow/Pages/MTO/Production/DueDateQuotation'
import OrderBalance from './VectorFlow/Pages/MTO/Production/InsightsAndTrends/OrderBalance'
import OTIFAnalysis from './VectorFlow/Pages/MTO/Poogi/InsightAndTrends/OTIFAnalysis'
import ResourceUtilization from './VectorFlow/Pages/MTO/Poogi/InsightAndTrends/ResourceUtilization'
import FOLSummary from './VectorFlow/Pages/MTO/Production/InsightsAndTrends/FOLSummary'
import DynamicReleaseManagement from './VectorFlow/Pages/MTO/Production/DynamicReleaseManagement'
import ReasonForDelayOrder from './VectorFlow/Pages/MTO/Poogi/ReasonOrderChange/index'
import TopFailureReasons from './VectorFlow/Pages/MTO/Poogi/InsightAndTrends/TopFailureReason'
import OTAndIFAnalysis from './VectorFlow/Pages/MTO/Poogi/InsightAndTrends/OTAndIFAnalysis'
import ElapsedTime from './VectorFlow/Pages/MTO/Production/InsightsAndTrends/ElapsedTime'
import LeadTime from './VectorFlow/Pages/MTO/Poogi/InsightAndTrends/LeadTime'
import TrendsOfFailureReason from './VectorFlow/Pages/MTO/Poogi/InsightAndTrends/TrendsOfFailureReason'
import OverallBmReport from './VectorFlow/Pages/MTO/Production/OverallBMReport'
import LandingPage from './VectorFlow/Pages/Common/LandingPage'
import MTOControlPanel from './VectorFlow/Pages/MTO/MDM/ControlPanel'
import MTOViewModify from './VectorFlow/Pages/MTO/MDM/ViewModify'
import MTOSavedDrafts from './VectorFlow/Pages/MTO/MDM/SavedDrafts'
import MTOTaskStatus from './VectorFlow/Pages/MTO/MDM/TaskStatus'
import MTOTaskPendingForReview from './VectorFlow/Pages/MTO/MDM/TaskPendingForReview'
import MTOAddRecord from './VectorFlow/Pages/MTO/MDM/AddRecord'
import MTODataModificationHistory from './VectorFlow/Pages/MTO/MDM/DataModificationHistory'
import MastersInterceptor from './VectorFlow/Pages/Common/MastersInterceptor'
import {AuthGate,UnAuthGate} from './components/VectorFLOW/layouts/VectorAdmin/AuthGate'
import VectorAdminLogin from './components/VectorFLOW/layouts/VectorAdmin/Login'
import Tools from './components/VectorFLOW/layouts/VectorAdmin/Tools'
import ManageRoles from './components/VectorFLOW/layouts/VectorAdmin/ManageRoles'
import ManageURLs from './components/VectorFLOW/layouts/VectorAdmin/ManageURLs'

import RRRColorBandwise from './VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/RationedRequirementReport  Color Bandwise'
import BuyerOrderReportColorBandwise from './VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/BuyerOrderReport Color Bandwise'
import SupplierWiseAllocation from './VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/SupplierWiseAllocation'

import OrderAllocationReport from './VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/OrderAllocationReport'
import TotalRequirementReport from './VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/TotalRequirementReport'
import BulkUploadPage from './module-store-transfer/pages/bulk-upload'
import ElephantOrder from './VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/ElephantOrders'
import Scheduling from './VectorFlow/Pages/MTO/Production/Scheduling'
import ManageEnvConfig from './components/VectorFLOW/layouts/VectorAdmin/ManageEnvConfig'
import FutureOrderLoadChart from './VectorFlow/Pages/MTO/Production/InsightsAndTrends/FutureOrderLoadChart'
import ManagePermissions from './components/VectorFLOW/layouts/VectorAdmin/ManagePermissions'
import ManageUIReportConfig from './components/VectorFLOW/layouts/VectorAdmin/ManageUIReportConfig'
import ManageUIMDMConfig from './components/VectorFLOW/layouts/VectorAdmin/ManageUIMDMConfig'
import { useUserData } from './context'
import AuditReport from './module-store-transfer/pages/Login-Audit-Report'

// to show loading state for desired page only instead of the entire screen
const lazyLoad = (children?: React.ReactNode) => {
  const search = window.location.search
  const params = new URLSearchParams(search)
  let lang = params.get('hl') || 'en'
  const langs = ['en', 'ja', 'es']
  if (lang && !langs.includes(lang)) lang = 'en'

  const authenPage = [
    '/login',
    '/forgot-password',
    '/change-password',
    '/profile',
    '/',
    '/landing-page'
  ]
  const urlAllPage = [
    ...authenPage,
    "/profile/bulk-upload",
    '/login-audit-report',
    '/',
    '/manual-upload',
    '/ist-forced-closure',
    '/store-status',
    '/availability-comparison',
    '/ist-status',
    '/permission-forbidden',
    '/mta/master-data-management/control-panel',
    '/mta/master-data-management/control-panel/view-modify',
    '/mta/master-data-management/saved-drafts',
    '/mta/master-data-management/task-status',
    '/mta/master-data-management/task-pending',
    '/mta/master-data-management/control-panel/add',
    '/mta/master-data-management/control-panel/delete',
    // mto mdm pages
    '/master-data-management/mto-control-panel',
    '/master-data-management/mto-control-panel/view-modify',
    '/master-data-management/mto-saved-drafts',
    '/master-data-management/mto-task-status',
    '/master-data-management/mto-task-pending',
    '/master-data-management/mto-control-panel/add',
    '/master-data-management/mto-control-panel/delete',
    //
    '/mta/supply-chain-intelligence-hub/bor',
    '/mta/supply-chain-intelligence-hub/bpr',
    '/mta/supply-chain-intelligence-hub/planning',
    '/mta/supply-chain-intelligence-hub/rrr',
    "/mta/supply-chain-intelligence-hub/open-expediting-requests",

    '/mta/supply-chain-intelligence-hub/rrr-color-bandwise',
    '/mta/supply-chain-intelligence-hub/bor-color-bandwise',
    '/mta/supply-chain-intelligence-hub/SupplierWiseAllocation',
    '/mta/supply-chain-intelligence-hub/order-allocation-report',
    '/mta/supply-chain-intelligence-hub/total-requirement-report',

    '/mta/insights-and-trends/buffer-trends',
    '/mta/insights-and-trends/guided-insights',
    '/mta/insights-and-trends/research-insights',
    '/mta/insights-and-trends/buffer-trend-report',
    '/mta/dbm/dbm-norm-suggestions',
    '/mta/logistics/intransit-whereabouts',

    '/mto/procurement/material-coverage-open-sales',
    '/mto/procurement-planning/planning',
    "/mto/procurement/insights-and-trends/day-wise-coverage",
    '/mto/planning/simulative-fullkit',
    '/mta/logistics/intransit-whereabouts',
    '/mto/procurement/material-requirement',
    '/mto/procurement/insights-and-trends/rmpm',
    '/mto/procurement/insights-and-trends/rmpm-buffer-trends',
    '/mto/procurement/insights-and-trends/rmpm-orderwise-coverage',
    '/mto/production-planning-and-scheduling/order-rescheduling',
    '/mto/procurement/insights-and-trends/rmpm-expediting-rm-suppliers',
    '/mto/production-planning-scheduling/enquiry-response',
    '/mto/production-planning-scheduling/insight-and-trends/bm-trends',

    '/mto/production-planning-scheduling/insight-and-trends/future-order-load-chart',


    '/mto/production-planning-scheduling/deptwise-bm-report',
    '/mto/production-planning-scheduling/insight-and-trends/stpl-full-kits',
    '/mto/production-planning-scheduling/full-kit-assignment',
    '/mta/supply-chain-intelligence-hub/sdr',
    '/mta/supply-chain-intelligence-hub/eo',
    '/mta/master-data-management/data-modification-history',
    '/supply-chain-intelligence-hub/merchandising-grid',
    '/mto/production-planning-and-scheduling/due-date-quotation',
    '/mto/production-planning-scheduling/insight-and-trends/order-at-risk',
    '/mto/production-planning-scheduling/insight-and-trends/order-balance',
    '/mto/poogi/insight-and-trends/resource-utilization-wip-profile',
    '/mto/poogi/insight-and-trends/otif-analysis',
    '/mto/production-planning-scheduling/insights-and-trends/fol-summary',
    '/mto/production-planning-scheduling/dynamic-release-mangement',
    '/mto/poogi/insight-and-trends/ot-and-if-analysis',
    '/mto/production-planning-scheduling/insights-and-trends/elapsed-time',
    '/mto/poogi/reasons-for-delayed-orders',
    '/mto/poogi/insight-and-trends/ot-and-if-analysis',
    '/mto/poogi/insight-and-trends/top-failure-reasons',
    '/mto/poogi/insight-and-trends/trend-of-failure-reason',
    '/mto/poogi/insight-and-trends/lead-time',
    '/mto/production-planning-scheduling/overall-bm-report',
    /**Delivery and Intelligence hub */
    '/mto/manufacturing-intelligence-hub/delivery-performance/bm-trends',
    '/mto/manufacturing-intelligence-hub/delivery-performance/otif-analysis',
    '/mto/manufacturing-intelligence-hub/delivery-performance/ot-and-if-analysis',
    '/mto/manufacturing-intelligence-hub/delivery-performance/lead-time',
    '/mto/manufacturing-intelligence-hub/future-order-load-chart',


    '/mto/manufacturing-intelligence-hub/congestion-analysis/elapsed-time',
    '/mto/manufacturing-intelligence-hub/congestion-analysis/orders-at-risk',
    '/mto/manufacturing-intelligence-hub/congestion-analysis/order-balance',

    '/mto/manufacturing-intelligence-hub/forward-exceution/fol-summary',
    '/mto/manufacturing-intelligence-hub/forward-exceution/stpl-and-fullkit',
    '/mto/manufacturing-intelligence-hub/forward-exceution/day-wise-coverage',
    '/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-order-wise-coverage',
    '/mto/manufacturing-intelligence-hub/forward-exceution/expetiting-rm-supplier',
    '/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-buffer-trend',

    '/mto/manufacturing-intelligence-hub/improvement-areas/top-failure-reasons',
    '/mto/manufacturing-intelligence-hub/improvement-areas/trends-failure-reasons',
    '/mto/manufacturing-intelligence-hub/improvement-areas/resource-wip-profile',
    '/landing-page',

    '/masters-interceptor/control-panel',
    "/masters-interceptor/saved-drafts",
    "/masters-interceptor/task-status",
    '/masters-interceptor/task-pending',
    "/masters-interceptor/data-modification-history",
    '/mto/master-data-management/control-panel',
    "/mto/master-data-management/control-panel/add",
    "/mto/master-data-management/control-panel/view-modify",
    "/mto/master-data-management/saved-drafts",
    "/mto/master-data-management/task-status",
    "/mto/master-data-management/task-pending",
    "/mto/master-data-management/data-modification-history",
    '/profile/bulk-upload',
    "/mto/production/scheduling"
  ]

  const {user: myUser} = useUserData();
  const urlPermissionArr:any =  myUser?.url_permission??[];

  const newUrlPermiss = [...authenPage, ...urlPermissionArr]

  const urlCurrent = window.location.pathname

  if (urlAllPage.includes(urlCurrent)) {
    if (newUrlPermiss.includes(urlCurrent)) {
      return (
        <Suspense fallback={<div className="d-flex vh-100">Loading...</div>}>
          {children}
        </Suspense>
      )
    } else {
      return <PageForbidden />
    }
  } else {
    return <PageNotFound />
  }
}

export const initRoutes = (): RouteObject[] => {
  const routes: RouteObject[] = []

  routes.push({ path: '/login', element: lazyLoad(<Login /> ) })
  routes.push({
    path: '/forgot-password',
    element: lazyLoad(<ForgotPassword /> )
  })
  routes.push({
    path: '/change-password',
    element: lazyLoad(<ChangePassword /> )
  })

  return [
    ...routes,
    // authenticated pages

    {
      path: '/',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<LandingPage/> )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/manual-upload',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<ManualUpload />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/ist-forced-closure',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<IstForced />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/store-status',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<StoreStatus />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/availability-comparison',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<Availability />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/ist-status',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<IstStatus />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/profile',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<Profile />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/login-audit-report',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<AuditReport />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },

    {
      path: '/profile/bulk-upload',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<BulkUploadPage />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/master-data-management/control-panel',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<ControlPanel />  )
        },
        {
          index: true,
          path: 'view-modify',
          element: lazyLoad(<ViewModify />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/master-data-management/saved-drafts',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<SavedDrafts />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/master-data-management/task-status',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<TaskStatus />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/master-data-management/task-pending',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<TaskPendingForReview />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/master-data-management/control-panel/add',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<AddRecord />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/master-data-management/control-panel/delete',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<DeleteRecord />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/master-data-management/data-modification-history',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<DataModificationHistory />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },

    // mto mdm pages
    {
      path: '/mto/master-data-management/control-panel',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<MTOControlPanel/>  )
        },
        {
          index: true,
          path: 'view-modify',
          element: lazyLoad(<MTOViewModify />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/master-data-management/saved-drafts',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<MTOSavedDrafts />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/master-data-management/task-status',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<MTOTaskStatus />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/master-data-management/task-pending',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<MTOTaskPendingForReview />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/master-data-management/control-panel/add',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<MTOAddRecord />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/master-data-management/data-modification-history',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<MTODataModificationHistory />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },


    //

     // interceptor pages
     {
      path: '/masters-interceptor/control-panel',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<MastersInterceptor key="master-data-management/control-panel" url={"/master-data-management/control-panel"}/>  )
        },
        {
          index: true,
          path: 'view-modify',
          element: lazyLoad(<MTOViewModify />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/masters-interceptor/saved-drafts',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<MastersInterceptor key="master-data-management/saved-drafts" url={'/master-data-management/saved-drafts'} />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/masters-interceptor/task-status',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<MastersInterceptor key="master-data-management/task-status" url={"/master-data-management/task-status"} />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/masters-interceptor/task-pending',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<MastersInterceptor key="master-data-management/task-pending" url={'/master-data-management/task-pending'} />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/master-data-management/control-panel/add',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<MTOAddRecord />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: "/masters-interceptor/data-modification-history",
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<MastersInterceptor key="master-data-management/data-modification-history" url={'/master-data-management/data-modification-history'} />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },


    //

    {
      path: '/mta/supply-chain-intelligence-hub/planning',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<Planning />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/supply-chain-intelligence-hub/planning',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<Planning />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/supply-chain-intelligence-hub/bpr',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<BPR />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/supply-chain-intelligence-hub/open-expediting-requests',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<OpenExpeditingRequests />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/supply-chain-intelligence-hub/merchandising-grid',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<MCGrid />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/logistics/intransit-whereabouts',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<InTransitWhereAbouts />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/not-found',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<PageNotFound />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/permission-forbidden',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<PageForbidden />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/supply-chain-intelligence-hub/bor',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<BuyerOrderReport />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/insights-and-trends/research-insights',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<ResearchInsights />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/supply-chain-intelligence-hub/rrr-color-bandwise',
      element:<AppLayout/>,
      children:[
        {
        index:true,
        element:lazyLoad(<RRRColorBandwise/>  )
        } ,
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/supply-chain-intelligence-hub/bor-color-bandwise',
      element:<AppLayout/>,
      children:[
        {
        index:true,
        element:lazyLoad(<BuyerOrderReportColorBandwise/>  )
        } ,
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/supply-chain-intelligence-hub/SupplierWiseAllocation',
      element:<AppLayout/>,
      children:[
        {
        index:true,
        element:lazyLoad(<SupplierWiseAllocation/>  )
        } ,
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/supply-chain-intelligence-hub/order-allocation-report',
      element:<AppLayout/>,
      children:[
        {
        index:true,
        element:lazyLoad(<OrderAllocationReport/>  )
        } ,
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/supply-chain-intelligence-hub/total-requirement-report',
      element:<AppLayout/>,
      children:[
        {
        index:true,
        element:lazyLoad(<TotalRequirementReport/>  )
        } ,
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/insights-and-trends/guided-insights',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<GuidedInsights />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/insights-and-trends/buffer-trend-report',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<BufferTrendReport />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/supply-chain-intelligence-hub/rrr',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<RRR />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/insights-and-trends/buffer-trends',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<BufferTrends />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/dbm/dbm-norm-suggestions',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<DBM />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/production-planning-scheduling/enquiry-response',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<EnquiryResponse /> )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/production-planning-scheduling/insight-and-trends/bm-trends',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<BMTrends />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },

    {
      path: '/mto/production-planning-scheduling/insight-and-trends/future-order-load-chart',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<FutureOrderLoadChart />)
        },
        ...getStoreTransferModuleRoutes()
      ]
    },


    {
      path: '/mto/production-planning-scheduling/insight-and-trends/stpl-full-kits',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<STPLAndFullKits />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/production-planning-scheduling/insight-and-trends/order-at-risk',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<OrderAtRisk />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/production-planning-scheduling/insight-and-trends/order-balance',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<OrderBalance />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/dbm/dbm-norm-suggestions',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<DBM />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/procurement/material-coverage-open-sales',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<MaterialCov />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/procurement-planning/planning',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<ProcurementPlanning />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/planning/simulative-fullkit',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<SimulateFullKit />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/procurement/insights-and-trends/day-wise-coverage',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<DayWiseCoverage />  )

        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/procurement/insights-and-trends/rmpm-orderwise-coverage',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<RMPMOrderwiseCoverage />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/procurement/material-requirement',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<MaterialRequirement />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },

    {
      path: '/mto/production-planning-scheduling/full-kit-assignment',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<FullKitAssignment />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/procurement/insights-and-trends/rmpm-buffer-trends',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<RMPMBufferTrends />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/production-planning-scheduling/deptwise-bm-report',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<DptWiseBMReport />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/procurement/insights-and-trends/rmpm-expediting-rm-suppliers',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<RMExpeditionSuppliers />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/supply-chain-intelligence-hub/sdr',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<SupplierDispatchReport />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mta/supply-chain-intelligence-hub/eo',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<ElephantOrder />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    }
    ,
    {
      path: '/mto/production-planning-and-scheduling/order-rescheduling',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<OrderRescheduling />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/poogi/insight-and-trends/resource-utilization-wip-profile',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<ResourceUtilization />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/poogi/insight-and-trends/otif-analysis',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<OTIFAnalysis />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/production-planning-scheduling/insights-and-trends/fol-summary',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<FOLSummary />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/production-planning-scheduling/dynamic-release-mangement',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<DynamicReleaseManagement />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/poogi/reasons-for-delayed-orders',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<ReasonForDelayOrder />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/production-planning-and-scheduling/due-date-quotation',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<DueDateQuotation />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/production-planning-scheduling/insights-and-trends/elapsed-time',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<ElapsedTime />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/poogi/insight-and-trends/ot-and-if-analysis',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<OTAndIFAnalysis />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/poogi/insight-and-trends/top-failure-reasons',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<TopFailureReasons />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/poogi/insight-and-trends/trend-of-failure-reason',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<TrendsOfFailureReason />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/poogi/insight-and-trends/lead-time',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<LeadTime />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/production-planning-scheduling/overall-bm-report',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<OverallBmReport />  )
        },
        ...getStoreTransferModuleRoutes()
      ]
    },
    {
      path: '/mto/manufacturing-intelligence-hub/delivery-performance/bm-trends',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<BMTrends />  )
        }
      ]
    },
    {
      path: '/mto/manufacturing-intelligence-hub/delivery-performance/otif-analysis',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<OTIFAnalysis />  )
        }
      ]
    },
    {
      path: '/mto/manufacturing-intelligence-hub/future-order-load-chart',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<FutureOrderLoadChart />)
        }
      ]
    },
    {
      path: '/mto/manufacturing-intelligence-hub/delivery-performance/ot-and-if-analysis',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<OTAndIFAnalysis />  )
        }
      ]
    },
    {
      path: '/mto/manufacturing-intelligence-hub/delivery-performance/lead-time',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<LeadTime />  )
        }
      ]
    },
    {
      path: '/mto/manufacturing-intelligence-hub/congestion-analysis/elapsed-time',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<ElapsedTime />  )
        }
      ]
    },
    {
      path: '/mto/manufacturing-intelligence-hub/congestion-analysis/orders-at-risk',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<OrderAtRisk />  )
        }
      ]
    },
    {
      path: '/mto/manufacturing-intelligence-hub/congestion-analysis/order-balance',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<OrderBalance />  )
        }
      ]
    },
    {
      path: '/mto/manufacturing-intelligence-hub/forward-exceution/fol-summary',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<FOLSummary />  )
        }
      ]
    },
    {
      path: '/mto/manufacturing-intelligence-hub/forward-exceution/stpl-and-fullkit',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<STPLAndFullKits />  )
        }
      ]
    },
    {
      path: '/mto/manufacturing-intelligence-hub/forward-exceution/day-wise-coverage',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<DayWiseCoverage />  )
        }
      ]
    },
    {
      path: '/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-order-wise-coverage',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<RMPMOrderwiseCoverage />  )
        }
      ]
    },
    {
      path: '/mto/manufacturing-intelligence-hub/forward-exceution/expetiting-rm-supplier',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<RMExpeditionSuppliers />  )
        }
      ]
    },
    {
      path: '/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-buffer-trend',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<RMPMBufferTrends />  )
        }
      ]
    },
    {
      path: '/mto/manufacturing-intelligence-hub/improvement-areas/top-failure-reasons',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<TopFailureReasons />  )
        }
      ]
    },
    {
      path: '/mto/manufacturing-intelligence-hub/improvement-areas/trends-failure-reasons',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<TrendsOfFailureReason />  )
        }
      ]
    },
    {
      path: '/mto/manufacturing-intelligence-hub/improvement-areas/resource-wip-profile',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<ResourceUtilization />  )
        }
      ]
    },
    {
      path: '/mto/production/scheduling',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<Scheduling/>  )
        }
      ]
    },
    {
      path: '/landing-page',
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: lazyLoad(<LandingPage />  )

        }
      ]},
      {
      path: '/vector-admin',
      element: <AuthGate />,
      children: [
        {
          index: true,
          element: <Tools/>,
          path:'/vector-admin'
        },
        {
          index: true,
          element: <ManageRoles/>,
          path:'/vector-admin/manage-roles'
        },
        {
          index: true,
          element: <ManageURLs/>,
          path:'/vector-admin/manage-urls'
        },
        {
          index: true,
          element: <ManageEnvConfig/>,
          path:'/vector-admin/manage-env-configuration'
        },
        {
          index: true,
          element: <ManagePermissions/>,
          path:'/vector-admin/manage-permissions'
        },
        {
          index: true,
          element: <ManageUIReportConfig/>,
          path:'/vector-admin/manage-ui-report-configuration'
        },
        {
          index: true,
          element: <ManageUIMDMConfig/>,
          path:'/vector-admin/manage-ui-mdm-configuration'
        }
      ]
    },
    {
      path: '/vector-admin/login',
      element: <UnAuthGate />,
      children: [
        {
          index: true,
          element: <VectorAdminLogin/>,
        }
      ]
    },
    {
      path: "*",
      element:< PageNotFound /> 
    }
  ]
}
