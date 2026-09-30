import { Outlet} from "react-router";
import { useLocation } from 'react-router-dom';
import {
  Header,
  NavbarTop,
  NavbarRight,
  NavbarMenu,
  NavbarItem,
} from "../../index";
import { useEffect, useState } from "react";
import { AuthenticationTemplate } from "./AuthenticationTemplate";
import * as GridSystem from "../../../styles/gridSystem";
import { ISTStatusContext } from "../../../context/ISTStatusContext";
import { useTranslation } from "react-i18next";
// import { listMenuParent } from "../NavbarMenu/listMenu";

const isAnonymous = false;

const AppLayout = () => {
  const { t } = useTranslation();

  const mtoPageUrls: any = ["/","/mto/master-data-management/control-panel/add","/mto/master-data-management/control-panel/view-modify","/mto/master-data-management/saved-drafts","/mto/master-data-management/task-status","/mto/master-data-management/task-pending","/mto/master-data-management/data-modification-history",'/master-data-management/mto-control-panel','/master-data-management/mto-control-panel/view-modify','/master-data-management/mto-saved-drafts','/master-data-management/mto-task-status','/master-data-management/mto-task-pending','/master-data-management/mto-control-panel/add', '/master-data-management/mto-control-panel/delete','/master-data-management/mto-control-panel/view-modify','/mto/procurement/material-coverage-open-sales', '/mto/production-planning-scheduling/insight-and-trends/order-at-risk', '/mto/production-planning-scheduling/insight-and-trends/stpl-full-kits', '/mto/production-planning-and-scheduling/order-rescheduling', '/mto/planning/simulative-fullkit', '/mto/procurement-planning/planning', '/mto/procurement/material-coverage-open-sales', '/mto/procurement/material-requirement', '/mto/procurement/insights-and-trends/rmpm-orderwise-coverage', '/mto/production-planning-scheduling/dynamic-release-mangement', "/mto/production-planning-and-scheduling/due-date-quotation","/mto/poogi/reasons-for-delayed-orders", "/mto/poogi/insight-and-trends/otif-analysis", '/mto/poogi/insight-and-trends/ot-and-if-analysis', '/mto/production-planning-scheduling/insights-and-trends/elapsed-time', '/mto/poogi/insight-and-trends/lead-time', '/mto/poogi/insight-and-trends/trend-of-failure-reason', '/mto/poogi/insight-and-trends/top-failure-reasons', "/mto/manufacturing-intelligence-hub/delivery-performance/otif-analysis", "/mto/manufacturing-intelligence-hub/delivery-performance/ot-and-if-analysis", "/mto/manufacturing-intelligence-hub/delivery-performance/lead-time", "/mto/manufacturing-intelligence-hub/congestion-analysis/elapsed-time", "/mto/manufacturing-intelligence-hub/improvement-areas/top-failure-reasons", "/mto/manufacturing-intelligence-hub/improvement-areas/trends-failure-reasons", "/mto/production-planning-scheduling/overall-bm-report", "/mto/production-planning-scheduling/deptwise-bm-report", "/landing-page","/mto/production/scheduling","/mto/manufacturing-intelligence-hub/future-order-load-chart","/mto/production-planning-scheduling/insight-and-trends/future-order-load-chart", "/login-audit-report"];
  //URL arrays for excluding layout padding
  // let urlDisableZoomScaling = ['/supply-chain-intelligence-hub/bpr','/supply-chain-intelligence-hub/merchandising-grid', '/logistics/intransit-whereabouts', '/supply-chain-intelligence-hub/planning', '/insights-and-trends/research-insights', '/insights-and-trends/buffer-trends', '/insights-and-trends/buffer-trend-report', "/insights-and-trends/guided-insights", "/production-planning-scheduling/enquiry-response", "/production-planning-scheduling/insight-and-trends/bm-trends", "/production-planning-scheduling/insight-and-trends/stpl-full-kits", "/production-planning-and-scheduling/order-rescheduling", "/production-planning-scheduling/full-kit-assignment", '/production-planning-scheduling/insight-and-trends/order-at-risk', '/procurement/insights-and-trends/rmpm-orderwise-coverage', "/production-planning-scheduling/insight-and-trends/order-balance", "/poogi/insight-and-trends/resource-utilization-wip-profile", "/production-planning-scheduling/insights-and-trends/fol-summary", "/manufacturing-intelligence-hub/delivery-performance/bm-trends", "/manufacturing-intelligence-hub/congestion-analysis/orders-at-risk", "/manufacturing-intelligence-hub/congestion-analysis/order-balance", "/manufacturing-intelligence-hub/forward-exceution/fol-summary", "/manufacturing-intelligence-hub/forward-exceution/stpl-and-fullkit", "/manufacturing-intelligence-hub/forward-exceution/rm-pm-order-wise-coverage", "/manufacturing-intelligence-hub/improvement-areas/resource-wip-profile"];
  let urlExcludePadding = ["/profile/bulk-upload" ,'/mta/supply-chain-intelligence-hub/SupplierWiseAllocation','/mta/supply-chain-intelligence-hub/rrr-color-bandwise','/mta/supply-chain-intelligence-hub/bor-color-bandwise','/mta/supply-chain-intelligence-hub/order-allocation-report','/mta/supply-chain-intelligence-hub/total-requirement-report','/supply-chain-intelligence-hub/merchandising-grid', '/mta/insights-and-trends/buffer-trends', '/mta/logistics/intransit-whereabouts', '/mta/supply-chain-intelligence-hub/sdr', '/mta/supply-chain-intelligence-hub/bor', '/mta/supply-chain-intelligence-hub/rrr', '/mta/supply-chain-intelligence-hub/open-expediting-requests', '/mta/master-data-management/control-panel/view-modify', '/mta/master-data-management/task-pending', '/mta/master-data-management/control-panel/add', '/mta/master-data-management/control-panel/delete', '/mta/supply-chain-intelligence-hub/bpr', '/mta/insights-and-trends/guided-insights', "/mta/insights-and-trends/buffer-trend-report", '/mta/insights-and-trends/research-insights', "/mto/procurement/insights-and-trends/rmpm", "/mto/procurement/insights-and-trends/rmpm-buffer-trends", "/mto/procurement/insights-and-trends/rmpm-expediting-rm-suppliers", "/mto/production-planning-and-scheduling/order-rescheduling", "/planning/simulative-fullkit", "/mto/procurement-planning/planning", '/mto/procurement/material-requirement', '/mto/procurement/insights-and-trends/rmpm-orderwise-coverage', "/mto/procurement/material-coverage-open-sales", "/mto/production-planning-scheduling/insight-and-trends/order-balance", "/mto/production-planning-scheduling/enquiry-response", "/mto/production-planning-scheduling/insight-and-trends/bm-trends", "/mto/production-planning-scheduling/insight-and-trends/order-at-risk", "/mto/production-planning-scheduling/insight-and-trends/order-balance", "/mto/production-planning-scheduling/enquiry-response", '/mto/poogi/insight-and-trends/resource-utilization-wip-profile', "/mto/production-planning-scheduling/insights-and-trends/fol-summary", "/mto/manufacturing-intelligence-hub/delivery-performance/bm-trends", "/mto/manufacturing-intelligence-hub/congestion-analysis/orders-at-risk", "/mto/manufacturing-intelligence-hub/congestion-analysis/order-balance", "/mto/manufacturing-intelligence-hub/forward-exceution/fol-summary", "/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-order-wise-coverage", "/mto/manufacturing-intelligence-hub/forward-exceution/expetiting-rm-supplier", "/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-buffer-trend", "/mto/manufacturing-intelligence-hub/improvement-areas/resource-wip-profile"];
  // const urlExclusdeHeader = ['/mta/master-data-management/control-panel/view-modify','/master-data-management/task-pending','/mta/master-data-management/control-panel/add','/mta/master-data-management/control-panel/delete','/supply-chain-intelligence-hub/bpr','/master-data-management/task-status','/master-data-management/saved-drafts'];
  let urlExclusdeHeader = ["/profile/bulk-upload" ,'/supply-chain-intelligence-hub/merchandising-grid', '/mto/procurement/material-coverage-open-sales', '/mta/master-data-management/task-pending', '/mta/master-data-management/task-status', '/mta/master-data-management/saved-drafts', "/mto/production-planning-scheduling/full-kit-assignment", '/mto/production-planning-scheduling/insight-and-trends/order-at-risk', "/mto/procurement-planning/planning", "/planning/simulative-fullkit", "/mto/procurement/material-requirement", "/mto/procurement/insights-and-trends/rmpm-orderwise-coverage", "/mto/procurement/insights-and-trends/day-wise-coverage", "/mto/procurement/insights-and-trends/rmpm-buffer-trends", "/mto/procurement/insights-and-trends/rmpm-expediting-rm-suppliers", "/mto/production-planning-scheduling/insight-and-trends/order-balance", "/mto/production-planning-scheduling/enquiry-response", "/mto/production-planning-and-scheduling/order-rescheduling", "/mto/production-planning-scheduling/insight-and-trends/bm-trends", "/mto/production-planning-scheduling/insight-and-trends/stpl-full-kits", "/mto/production-planning-scheduling/insight-and-trends/order-balance", "/mto/production-planning-scheduling/deptwise-bm-report", '/mto/poogi/insight-and-trends/resource-utilization-wip-profile', "/mto/production-planning-scheduling/insights-and-trends/fol-summary", "/mto/poogi/reasons-for-delayed-orders", "/mto/production-planning-scheduling/overall-bm-report", "/mto/manufacturing-intelligence-hub/delivery-performance/bm-trends", "/mto/manufacturing-intelligence-hub/congestion-analysis/orders-at-risk", "/mto/manufacturing-intelligence-hub/congestion-analysis/order-balance", "/mto/manufacturing-intelligence-hub/forward-exceution/fol-summary", "/mto/manufacturing-intelligence-hub/forward-exceution/stpl-and-fullkit", "/mto/manufacturing-intelligence-hub/forward-exceution/day-wise-coverage", "/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-order-wise-coverage", "/mto/manufacturing-intelligence-hub/forward-exceution/expetiting-rm-supplier", "/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-buffer-trend", "/mto/manufacturing-intelligence-hub/improvement-areas/resource-wip-profile"];

  // urlDisableZoomScaling = [...urlDisableZoomScaling, ...mtoPageUrls];   Zoom is no longer needed
  urlExcludePadding = [...urlExcludePadding, ...mtoPageUrls];
  urlExclusdeHeader = [...urlExclusdeHeader, ...mtoPageUrls];

  const location = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);


  const [currentViewCount, setCurrentViewCount] = useState(0);
  const [currentDataCount, setCurrentDataCount] = useState(0);
  const [currentAction, setCurrentAction] = useState("edit");
  const [exportView, setExportView] = useState(false);
  const [currentViewName, setCurrentViewName] = useState(
    t("ISTStatus.viewName") as string
  );
  const [widthResponsive, setWidthResponsive] = useState<object>({
    widthLeft: "0%",
    widthRight: "95%",
  });

  const [isOpenNavbarRight, setIsOpenNavbarRight] = useState<boolean>(false);
  const [isLoadSpinner, setIsLoadSpinner] = useState<any>(false);
  const [menuItem, setMenuItem] = useState<any>();
  const [colorTheme, setColorTheme] = useState<string>("NOIRFUSION");
  const [isHide, setIsHide] = useState<boolean>(false);



  return (
    <AuthenticationTemplate
      loadingComponent={<>Loading...</>}
      isAnonymous={isAnonymous}
      setMenuItem={setMenuItem}
    >
      <NavbarRight
        isOpenNavbarRight={isOpenNavbarRight}
        setIsOpenNavbarRight={setIsOpenNavbarRight}
        setColorTheme={setColorTheme}
        isLoadSpinner={isLoadSpinner}
        setIsLoadSpinner={setIsLoadSpinner}
      />
      <GridSystem.SCGrid>
        <GridSystem.SCFullScreen>
          <NavbarTop
            setIsOpenNavbarRight={setIsOpenNavbarRight}
            setIsLoadSpinner={setIsLoadSpinner}
            isLoadSpinner={isLoadSpinner}
          />
        </GridSystem.SCFullScreen>
        <GridSystem.SCRow>
          <GridSystem.SCCol1 colorTheme={colorTheme}>
            <NavbarMenu setMenuItem={setMenuItem} isHide={isHide} setIsHide={setIsHide} setWidthResponsive={setWidthResponsive} menuItem={menuItem}/>
          </GridSystem.SCCol1>
          <GridSystem.SCCol2 width={widthResponsive} colorTheme={colorTheme}>
            <NavbarItem
              setWidthResponsive={setWidthResponsive}
              menuItem={menuItem}
              isHide={isHide}
              setIsHide={setIsHide}
            />
          </GridSystem.SCCol2>
          <GridSystem.SCCol8 width={widthResponsive} hidePadding={urlExcludePadding.includes(location.pathname)} disableZoomScaling={true}>
            <ISTStatusContext.Provider
              value={{
                currentAction,
                setCurrentAction,
                exportView,
                setExportView,
                currentViewName,
                setCurrentViewName,
                currentViewCount,
                setCurrentViewCount,
                currentDataCount,
                setCurrentDataCount,
              }}
            >
              <Header urlExcludeHeader={urlExclusdeHeader} />
              <Outlet />
            </ISTStatusContext.Provider>
          </GridSystem.SCCol8>
        </GridSystem.SCRow>
      </GridSystem.SCGrid>
    </AuthenticationTemplate>
  );
};

export default AppLayout;
