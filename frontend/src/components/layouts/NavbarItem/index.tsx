import * as NavStyle from "./styles";
import { useState, useCallback } from "react";
import { SCMenuLeft, SCMenuItem, SCItemChild } from "./styles";
import { useLocation, useNavigate } from "react-router-dom";
import { useUserData } from "../../../context";
import Particulars from "./particulars";
import { useTranslation } from "react-i18next";
import { ColumnChart } from "../../index";
import ParticularForced from "./ParticularForced";
import ParticularStoreStatus from "./ParticularStoreStatus";
import ParticularAvai from "./ParticularAvai";
import { navigateWithPrompt } from '../../../helpers/utils'
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from "../../../redux/store/store";
import { RESET_STATE } from "../../../redux/actions/MDM";
import BPRDailyAnalytics from "../../../components/VectorFLOW/layouts/BPRDailyAnalytics";
import InTransitAnalytics from "../../../VectorFlow/Pages/MTA/Logistics/InTransitWhereAbouts/InTransitAnalytics";
import OpenExpediteAnalytics from "../../../VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/OpenExpeditingRequests/OpenExpediteAnalytics";
import RRRAnalytics from "../../../VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/RationedRequirementReport/RRRAnalytics";
import BORAnalytics from "../../../VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/BuyerOrderReport/BORAnalytics";
import DBMAnalytics from "../../../VectorFlow/Pages/MTA/DBM/DBMNormSuggestions/DBMAnalytics";
import AnalyticalScreen from "../../../VectorFlow/Pages/MTO/Procurement/MaterialCoverage/AnalyticalScreen";
import ReasonsOrderAnalyticalScreen from "../../../VectorFlow/Pages/MTO/Poogi/ReasonOrderChange/ReaonsOrderAnalyticalScreen";
import DaywiseCoverageAnalytics from "../../../VectorFlow/Pages/MTO/Procurement/InsightsAndTrends/DayWiseCoverage/DayWiseCoverageAnalytics";
import ProcAnalytics from "../../../VectorFlow/Pages/MTO/Procurement/Planning/ProcAnalytics";
import SimAnalyticalScreen from "../../../VectorFlow/Pages/MTO/Procurement/Planning/SimulateFullKit/SimulateAnalytics";
import DDQAnalytics from "../../../VectorFlow/Pages/MTO/Production/DueDateQuotation/DDQAnalytics";
import DRMAnalytics from "../../../VectorFlow/Pages/MTO/Production/DynamicReleaseManagement/DRMAnalytics";
import DeptWiseAnalytics from "../../../VectorFlow/Pages/MTO/Production/DepartmentWiseBMReport/DeptWiseAnalytics";
import ResourceUtilAnalytics from "../../../VectorFlow/Pages/MTO/Poogi/InsightAndTrends/ResourceUtilization/ResourceUtilAnalytics";
import { RESET_MTO_STATE } from "../../../redux/actions/MTO";

const NavbarItem = ({
  setWidthResponsive,
  menuItem,
  isHide,
  setIsHide,
}: any) => {
  const { t } = useTranslation();
  const { user, isSideBarOpen, toggleSideBar } = useUserData();
  const permission: any = user?.roles?.permission;
  const { currentView, currentCategory } = useSelector((state: RootState) => state.mta.planning)
  // const analyticsPaths: Array<string> = ["/mta/supply-chain-intelligence-hub/bpr", "/mta/insights-and-trends/research-insights", "/mta/insights-and-trends/buffer-trend-report", "/mta/insights-and-trends/buffer-trends"]
  const analyticsPaths: Array<string> = ["/mta/supply-chain-intelligence-hub/bpr"]
  const themeUi = user?.user?.theme_ui;
  const navigate = useNavigate();
  const location = useLocation();
  const { pathname } = useLocation();

  const mdm = useSelector((state: RootState) => state.mdm);
  const dispatch = useDispatch();


  const resetState = () => {
    dispatch(RESET_STATE());
    dispatch(RESET_MTO_STATE());
  }
  const RenderListMenu = (props: { listMenu: any }) => {

    const [toggle, setToggle] = useState(true);
    const {
      listMenu
    } = props

    const allChildUrls = listMenu?.child?.map((i: any) => i.url);
    
    const hasChild = listMenu.child.find((listChild: any) => {
      return Object.prototype.hasOwnProperty.call(listChild, 'child');
    })

    if (!hasChild && !allChildUrls?.some((url: string) => user?.url_permission.includes(url))) {
      return null;
    }
    
    return (
      <SCMenuItem
        key={listMenu.id}
        active={
          listMenu.url === location.pathname ||
          listMenu.child.some((i: any) => i.url === location.pathname)
        }
      >
        <>
          {
            !listMenu.avoidHeader && (
              <NavStyle.SCNavMenu
                onClick={() => setToggle(!toggle)}
                className={`${toggle ? "active" : ""}`}
              >
                <NavStyle.SCInterStore themeUi={themeUi}>
                  {t(listMenu.name)}
                </NavStyle.SCInterStore>
                <NavStyle.SCInterStoreArrowDown
                  toggle={toggle}
                  src="/assets/img/nav/arrow_down.svg"
                />
              </NavStyle.SCNavMenu>
            )
          }
          {
            listMenu.child.map((l: any, index: number) => {
              if (l.child && l.child.length>0) {
                return (
                  <RenderListMenu listMenu={l} key={index} />
                )
              }
              return renderListMenuChild([l], toggle)
            })
          }

        </>
      </SCMenuItem>
    );
  };


  const renderAnalyticsGrid = useCallback(() => {
    // if (location.pathname === "/mta/supply-chain-intelligence-hub/planning") {

    //   if (currentView !== 'chart' && currentCategory !== "") {
    //     return true
    //   }
    //   if (currentCategory === "") {
    //     return true
    //   }
    // }
    return analyticsPaths.includes(pathname);
  }, [pathname]);


  const renderListMenuChild = (listChild: any, status: boolean) => {
    return listChild.map((item: any) => {

      const checkForUrl = user?.url_permission.includes(item?.url);
      if (checkForUrl) {
        return (
          <SCItemChild
            key={item.url}
            onClick={() => {
              navigateWithPrompt(() => {
                navigate(item.url, { replace: true });
                if (isHide) {
                  setWidthResponsive({
                    widthLeft: "0%",
                    widthRight: "95%",
                  });
                } else {
                  setWidthResponsive({
                    widthLeft: "20%",
                    widthRight: "75%",
                  });
                }
                setIsHide(!isHide);
                toggleSideBar(!isSideBarOpen)

              }, item.url, mdm, resetState);
            }}
            active={item.url === location.pathname}
            status={status}
            themeUi={themeUi}
          >
            <NavStyle.SCNavChild
              themeUi={themeUi}
              active={item.url === location.pathname}
            >
              {" "}
              {t(item.name)}
            </NavStyle.SCNavChild>
            {!(item.url === location.pathname) && (
              <NavStyle.SCInputIcon src={item.img} />
            )}

          </SCItemChild>
          //  {item.child && (
          //   <React.Fragment>
          //   {item.child.map((i:any,index:number)=>{
          //     return (
          //       <React.Fragment>
          //         {renderListMenu(i)}
          //       </React.Fragment>
          //     )
          //   })}
          // </React.Fragment>
          // )}
        );
      }
    });
  };

  // const activeCollapseItem = () => {
  //   setToggle(!toggle);
  // };

  const handleClickIconMenu = () => {
    if (isHide) {
      setWidthResponsive({
        widthLeft: "0%",
        widthRight: "95%",
      });
    } else {
      setWidthResponsive({
        widthLeft: "20%",
        widthRight: "75%",
      });
    }
    setIsHide(!isHide);
    toggleSideBar(!isSideBarOpen)
  };

  return (
    <NavStyle.SCGridNav
      id="vector_nav"
      className="list-roles-per--content"
      isHide={isHide}
      pathname={pathname}
    >
      <NavStyle.SCNavbar>
        <NavStyle.SCNavBox>
          <NavStyle.SCBoxTop>
            {isHide && (
              <NavStyle.SCText themeUi={themeUi}>COMPONENTS</NavStyle.SCText>
            )}
            <NavStyle.SCIconMenu
              src={`/assets/img/nav/icon_hide_menu${themeUi === "REGALBLAZE" ? "_yellow" : ""
                }.svg`}
              alt="menu"
              onClick={handleClickIconMenu}
              themeUi={themeUi}
              isHide={isHide}
            />
          </NavStyle.SCBoxTop>
          {isHide && !!menuItem && (
            <SCMenuLeft><RenderListMenu listMenu={menuItem} /></SCMenuLeft>
          )}
        </NavStyle.SCNavBox>
        {isHide && renderAnalyticsGrid() && menuItem.id === 9 && (
          <BPRDailyAnalytics
            colDefs={[
              {
                headerName: '',
                colId: 'color'
              },
              {
                headerName: 'On-Hand.'
              },
              {
                headerName: 'Pipeline.'
              },
            ]}
          />
        )}

        {/* {isHide && pathname === '/mta/logistics/intransit-whereabouts' && menuItem.id === 9 && (
          <InTransitAnalytics />
        )} */}

        {isHide && pathname === '/mto/procurement/material-coverage-open-sales' && menuItem.id === 19 && (
          <AnalyticalScreen pageName="MaterialSO" />
        )}

        {isHide && pathname === '/mto/production-planning-and-scheduling/due-date-quotation' && menuItem.id === 10 && (
          <DDQAnalytics />
        )}

        {isHide && pathname === '/mto/production-planning-scheduling/overall-bm-report' && menuItem.id === 10 && (
          <DeptWiseAnalytics />
        )}

        {isHide && pathname === '/mto/production-planning-scheduling/full-kit-assignment' && menuItem.id === 10 && (
          <AnalyticalScreen pageName="Fullkit assignment" />
        )}
        {isHide && pathname === '/mto/production-planning-scheduling/dynamic-release-mangement' && menuItem.id === 10 && (
          <DRMAnalytics />
        )}

        {isHide && pathname === '/mto/production-planning-scheduling/deptwise-bm-report' && menuItem.id === 10 && (
          <DeptWiseAnalytics />
        )}

        {isHide && pathname === '/mto/planning/simulative-fullkit' && menuItem.id === 19 && (
          <SimAnalyticalScreen />
        )}

        {isHide && pathname === '/mto/procurement-planning/planning' && menuItem.id === 19 && (
          <ProcAnalytics />
        )}



        {isHide && pathname === '/mto/procurement/insights-and-trends/day-wise-coverage' && menuItem.id === 19 && (
          <DaywiseCoverageAnalytics />
        )}

        {/* {isHide && pathname === '/mta/supply-chain-intelligence-hub/rrr' && menuItem.id === 9 && (
          <RRRAnalytics />
        )}

        {isHide && pathname === '/mta/supply-chain-intelligence-hub/bor' && menuItem.id === 9 && (
          <BORAnalytics />
        )}

        {isHide && pathname === "/mta/dbm/dbm-norm-suggestions" && menuItem.id === 9 && (
          <DBMAnalytics />
        )}

        {isHide && pathname === '/mta/supply-chain-intelligence-hub/open-expediting-requests' && menuItem.id === 9 && (
          <OpenExpediteAnalytics />
        )} */}

        {isHide && pathname === "/ist-forced-closure" && menuItem.id === 6 && (
          <ParticularForced themeUi={themeUi} />
        )}

        {isHide && pathname === "/store-status" && menuItem.id === 6 && (
          <ParticularStoreStatus themeUi={themeUi} />
        )}

        {isHide &&
          pathname === "/availability-comparison" &&
          menuItem.id === 6 && <ColumnChart themeUi={themeUi} />}

        {isHide && pathname === "/availability-comparison" && menuItem.id === 6 && (
          <ParticularAvai themeUi={themeUi} />
        )}

        {isHide && pathname === '/mto/poogi/reasons-for-delayed-orders' && menuItem.id === 11 && (
          <ReasonsOrderAnalyticalScreen />
        )}
        {isHide && pathname === '/mto/poogi/insight-and-trends/resource-utilization-wip-profile' && menuItem.id === 11 && (
          <ResourceUtilAnalytics />
        )}


        {pathname === "/" || pathname === "/ist-status" ? (
          <>
            {isHide && menuItem.id === 6 ? (
              <>
                {permission?.includes("IST Admin") ||
                  permission?.includes("IST Liaison") ||
                  permission?.includes("IST Governor") ? (
                  <Particulars themeUi={themeUi} />
                ) : (
                  <></>
                )}
              </>
            ) : (
              <></>
            )}
          </>
        ) : (
          <></>
        )}
      </NavStyle.SCNavbar>
    </NavStyle.SCGridNav>
  );
};

export default NavbarItem;