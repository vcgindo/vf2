import * as NavStyle from "./styles";
import { useQueryClient } from "@tanstack/react-query";
import { MainService } from "../../../module-main/services/api";
import { listMenuParent } from "./listMenu";
import { MenuToolTip } from "../../../components/index";
import { useState, useEffect } from "react";
import { useUserData } from "../../../context";
import { useLocation, useNavigate } from "react-router";
import { useGetAllReports } from '../../../VectorFlow/Services/MTA/MDM'
import _ from 'lodash'
import { useGetAllMTOReports } from "../../../VectorFlow/Services/MTO/Common/DownloadReports";
import { getNestedChildren } from "../../../helpers/utils";
import { Tooltip } from 'react-tooltip';
import { decryptStorageData, encryptStorageData } from "../../../VectorFlow/Pages/MTO/Common/encryption";

const NavbarMenu = ({ setMenuItem, isHide, setIsHide, setWidthResponsive, menuItem }: any) => {
  const { mutateAsync: getAllReports } = useGetAllReports();
  const {mutateAsync: getAllMTOReports} = useGetAllMTOReports();
  const [listMenu, setListMenu] = useState(()=>{
    if(menuItem){
      
      const updatedMenu = listMenuParent.map((item: any) => ({
        ...item,
        status: item.id === menuItem.id,
      }));
      return updatedMenu;
    } else {
      return listMenuParent;
    }
  });
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  const queryClient = useQueryClient();
  const { user, setUser } = useUserData();
  const themeUi = user?.user?.theme_ui;
  const [activeTooltip, setActiveTooltip] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(false);
  const [tempUrls, setTempUrls] = useState([]); //temp url is used to show downloading
  const [reportUrls, setReportUrls] = useState<string[]>([]);

  const location = useLocation();       
   useEffect(()=>{
    setListMenu((prev:any[])=>{
      const updatedPrev = prev.map((list)=>{
        return {
          ...list,
          status : list.url === location.pathname
        }
      })
      return updatedPrev
    })
  },[location])

  const getReportFields = async () => {
    try {
      const [reportsResponse, mtoReportsResponse] = await Promise.allSettled([
        getAllReports(),
        getAllMTOReports(),
      ]);
  
      let transformedData: any[] = [];
      let transformedMTOData: any[] = [];
  
      // Process normal reports if the request succeeded
      if (reportsResponse.status === "fulfilled" && reportsResponse.value.status === 200) {
        const rawDailyReport = reportsResponse.value.data.data;
        transformedData = Object.entries(rawDailyReport).map(([key, attributes]: [string, any]) => ({
          name: attributes.reportName,
          img: "/assets/img/nav/arrow_down.svg",
          imgHover: "/assets/img/nav/DownloadReport-Icon.svg",
          url: key,
          role: ["IST Admin", "IST Requestor", "IST Governor", "IST Liaison", "Admin", "VectorConsultant", "DBMManager", "BPRManager", "MasterUpdater", "MasterApprover"],
          downloadName: attributes.downloadName
        }));
      } else {
        if (reportsResponse.status === "rejected") {
          console.error("Error fetching reports:", reportsResponse.reason);
        }
      }
      // Process MTO reports if the request succeeded
      if (mtoReportsResponse.status === "fulfilled" && mtoReportsResponse.value.status === 200) {
        const rawMTOReports = mtoReportsResponse.value.data.data;
        transformedMTOData = Object.entries(rawMTOReports).map(([key, attributes]: [string, any]) => ({
          name: attributes.reportName,
          img: "/assets/img/nav/arrow_down.svg",
          imgHover: "/assets/img/nav/DownloadReport-Icon.svg",
          url: key,
          role: ["IST Admin", "IST Requestor", "IST Governor", "IST Liaison", "BMReportManager"],
          isMTO: true,
          downloadName: attributes.downloadName
        }));
      } else {
        if (mtoReportsResponse.status === "rejected") {
          console.error("Error fetching MTO reports:", mtoReportsResponse.reason);
        }
      }
  
      // Clone the menu once and update it
      const updatedMenu = _.cloneDeep(listMenuParent).map((item: any) => {
        if(menuItem){

          return {
            ...item,
            status: item.id === menuItem.id,
          };
        }else{
          return item;
        }
      });
      const targetObject = updatedMenu.find((item: any) => item.id === 8);
  
      if (targetObject) {

        if(user.url_permission.includes('mta-report-urls')){
        targetObject.child.push(...transformedData);
        }
        if(user.url_permission.includes('mto-report-urls')){
          targetObject.child.push(...transformedMTOData);
        }
        const reportUrlsCombined = targetObject.child.map((child: any) => child.url).filter((url: string) => url);

        setReportUrls(reportUrlsCombined);
      }
  
      setListMenu(updatedMenu);
    } catch (err) {
      console.error("Unexpected error in getReportFields:", err);
    }
  };

  // const getReportFields = async () => {
  //   let transformedData: any = undefined;

  //   try {
  //     const reports = await getAllReports();
  //     const rawDailyReport = reports.data.data;
  //     transformedData = Object.entries(rawDailyReport).map(([key, attributes]: [string, any]) => ({
  //       name: attributes.reportName,
  //       img: "/assets/img/nav/arrow_down.svg",
  //       imgHover: "/assets/img/nav/DownloadReport-Icon.svg",
  //       url: key,
  //       role: ["IST Admin", "IST Requestor", "IST Governor", "IST Liaison", "Admin", "VectorConsultant", "DBMManager", "BPRManager", "MasterUpdater", "MasterApprover"],
  //       downloadName: attributes.downloadName
  //     }));
  //     const extractedNewMenu = _.cloneDeep(listMenuParent)
  //     const targetObject = extractedNewMenu.find((item: any) => item.id === 8);
  //     if (targetObject) {
  //       targetObject.child.push(...transformedData);
  //       const reporturls = targetObject.child.map((child: any) => child.url).filter((url: string) => url);
  //       setReportUrls(reporturls)
  //     }
  //     setListMenu(extractedNewMenu);
  //   } catch (err) {
  //     console.error("Error fetching reports", err);
  //   } finally {
  //     try {
  //       const mtoReports = await getAllMTOReports();
  //       const rawMTOReports = mtoReports.data.data;
  //       const transformedMTOData = Object.entries(rawMTOReports).map(([key, attributes]: [string, any]) => ({
  //         name: attributes.reportName,
  //         img: "/assets/img/nav/arrow_down.svg",
  //         imgHover: "/assets/img/nav/DownloadReport-Icon.svg",
  //         url: key,
  //         role: ["IST Admin", "IST Requestor", "IST Governor", "IST Liaison", "BMReportManager"],
  //         isMTO: true,
  //         downloadName: attributes.downloadName
  //       }));

  //       const extractedNewMenu = _.cloneDeep(listMenuParent);
  //       const targetObject = extractedNewMenu.find((item: any) => item.id === 8);
  //       if (targetObject) {
  //         if (transformedData) {
  //           targetObject.child.push(...transformedData);
  //         }
  //         targetObject.child.push(...transformedMTOData);
  //         const reporturls = targetObject.child.map((child: any) => child.url).filter((url: string) => url);
  //         setReportUrls(reporturls);
  //       }
  //       setListMenu(extractedNewMenu);
  //     } catch (error) {
  //       console.log(error);
  //     }
  //   }
  // };

  // const getReportFields = async () => {
  //   const reports = await getAllReports();
  //   const rawDailyReport = reports.data.data
  //   const transformedData = Object.entries(rawDailyReport).map(([key, attributes]: [string, any]) => ({
  //     name: attributes.reportName,
  //     img: "/assets/img/nav/arrow_down.svg",
  //     imgHover: "/assets/img/nav/DownloadReport-Icon.svg",
  //     url: key,
  //     role: ["IST Admin", "IST Requestor", "IST Governor", "IST Liaison", "Admin", "VectorConsultant", "DBMManager", "BPRManager", "MasterUpdater", "MasterApprover"],
  //     downloadName: attributes.downloadName
  //   }));
  //   const extractedNewMenu = _.cloneDeep(listMenuParent)
  //   const targetObject = extractedNewMenu.find((item: any) => item.id === 8);
  //   if (targetObject) {
  //     targetObject.child.push(...transformedData);
  //     const reporturls = targetObject.child.map((child: any) => child.url).filter((url: string) => url);
  //     setReportUrls(reporturls)
  //   }
  //   setListMenu(extractedNewMenu);
  // }
  
  useEffect(() => {
    // Define an async function to load and decrypt data
    const loadDataFromStorage = async () => {
      try {
        // --- DECRYPTING ListItem ---
        const encryptedItem = localStorage.getItem("ListItem");
        if (encryptedItem) {
          // 1. Decrypt the string
          const decryptedItem = await decryptStorageData(encryptedItem);
          if (decryptedItem) {
            setMenuItem(
              typeof decryptedItem === "string"
                ? JSON.parse(decryptedItem)
                : decryptedItem
            );
          } else {
            localStorage.removeItem("ListItem");
          }
        }
  
        // --- DECRYPTING ListMenu ---
        const encryptedMenu = localStorage.getItem("ListMenu");
        if (encryptedMenu) {
          // 1. Decrypt the string
          const decryptedMenu = await decryptStorageData(encryptedMenu);
          if (decryptedMenu) {
            setListMenu(
              typeof decryptedMenu === "string"
                ? JSON.parse(decryptedMenu)
                : decryptedMenu
            );
          } else {
            localStorage.removeItem("ListMenu");
          }
        }
      } catch (error) {
        console.error("Failed to load or parse encrypted data from storage:", error);
      }
    };
  
    getReportFields();
    loadDataFromStorage(); // Call the async function
  
  }, [listMenuParent]);

  // Add the 'async' keyword to the function definition
const handleClickMenu = async (item: any, index: number) => {
  if (item.name === 'navbar.listMenuParent.miscellaneousReports.title') return;
  setMenuItem(item);
  const newMenu = [...listMenu];
  newMenu.forEach((itemMenu: any) => {
    itemMenu.status = false;
  });
  newMenu[index].status = true;

  // --- ENCRYPTION LOGIC ---
  // 1. Stringify the object/array first
  const itemString = JSON.stringify(item);
  const menuString = JSON.stringify(newMenu);

  // 2. Encrypt the resulting string
  const encryptedItem = await encryptStorageData(itemString);
  const encryptedMenu = await encryptStorageData(menuString);

  // 3. Save the encrypted string to localStorage
  localStorage.setItem("ListItem", encryptedItem);
  localStorage.setItem("ListMenu", encryptedMenu);

  setListMenu(newMenu);
  handleItemLeave();
};

  const navigateTo = useNavigate();
  
  const handleLogout = async () => {
    const response = await MainService.logout(false, queryClient);
    if (response?.status == 204) {
      setUser(undefined);
    }
    navigateTo("/login");
  };

  const handleItemHover = (e: any, id: number) => {
    setActiveTooltip(id);
  };

  const handleItemLeave = () => {
    setActiveTooltip(0);
  };


  const renderImg = (src: string, active: boolean, id: number) => {
    let srcImg: string;
    if (themeUi === "CHARCOALCHIC" && active && id === 6) {
      srcImg = src + "_CHARCOALCHIC_active.svg";
    } else if (themeUi === "PUREELEGANCE") {
      srcImg = src + "_black.svg";
    } else {
      srcImg = src + ".svg";
    }
    return srcImg;
  };

  const getChild = (item: any): { url: string } | undefined => {
    let childMenuItem;
  
    const result = getNestedChildren(item.child);

    result.some((itemChild: any) => {
      if (
        (user.url_permission.includes(itemChild.url) ||
          reportUrls.includes(itemChild.url))
      ) {
        childMenuItem = itemChild;
        return true;
      }
    })
    return childMenuItem;
  }

  const navigate = useNavigate();

  return (
    <NavStyle.SCGridNav id="vector_nav" className="list-roles-per--content">
      <NavStyle.SCNavBox>
        {listMenu.map((item: any, index: number) => {

          const childMenu = getChild(item);
          
          if (childMenu) {
            return (
              <NavStyle.SCMenuItem
                key={item.id}
                active={item.status}
                themeUi={themeUi}
                onMouseEnter={(e) => handleItemHover(e, item.id)}
                onMouseLeave={handleItemLeave}
              >
                <NavStyle.SCNavMenu
                  onClick={() => handleClickMenu(item, index)}
                >
                  <NavStyle.SCNavIcon
                    data-tooltip-id={item.name}
                    src={renderImg(item.img, item.status, item.id)}
                    alt="logo"
                    style={{ zoom: item.id == `11` || item.id == `12` ? 1.2 : 1 }}
                    widthIcon={item.widthIcon}
                    onClick={() => { item.id !== 8 ? navigate(childMenu.url): '' }}

                  />
                  {!item.status && activeTooltip === item.id && (
                    <MenuToolTip 
                      reportUrls={reportUrls} 
                      item={item} 
                      isLoading={isLoading} 
                      setIsLoading={setIsLoading} 
                      tempUrls={tempUrls} 
                      setTempUrls={setTempUrls} 
                      isHide={isHide} 
                      setIsHide={setIsHide} 
                      setWidthResponsive={setWidthResponsive}
                    />
                  )}
                  {item.status && !isHide && activeTooltip === item.id && (
                    <MenuToolTip 
                      reportUrls={reportUrls} 
                      item={item} 
                      isLoading={isLoading} 
                      setIsLoading={setIsLoading} 
                      tempUrls={tempUrls} 
                      setTempUrls={setTempUrls} 
                      isHide={isHide} 
                      setIsHide={setIsHide} 
                      setWidthResponsive={setWidthResponsive} 
                    />
                  )}
                </NavStyle.SCNavMenu>
              </NavStyle.SCMenuItem>
            );
          }
        })}
      </NavStyle.SCNavBox>
      <NavStyle.SCNavLogout onClick={handleLogout}>
        <NavStyle.SCIconLogout data-tooltip-id = {"logout-tooltip"} src="/assets/img/nav/logout.png" alt="Logout" />
        <Tooltip id="logout-tooltip" place="right" content={"Logout"} className="logout-tooltip" />
      </NavStyle.SCNavLogout>
    </NavStyle.SCGridNav>
  );
};

export default NavbarMenu;
