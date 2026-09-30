import { Tooltip } from "react-tooltip";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";
import { useUserData } from "../../../context";
import {
  WrapToolTip,
  TooltipContainer,
  TooltipTitle,
  TooltipContent,
  SCIcon,
} from "./style";
import { navigateWithPrompt } from "../../../helpers/utils";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../../redux/store/store";
import { RESET_STATE } from "../../../redux/actions/MDM";
import { RESET_MTO_STATE } from "../../../redux/actions/MTO";
import { useRef, useLayoutEffect, useState } from "react";
import useDownloadHandler from "../../../helpers/useDownloadHandler";
 
const ITEM_HEIGHT = 48; // Adjust to match your TooltipContent height
const MIN_VISIBLE_ITEMS = 5;
 
const MenuToolTip = ({
  item,
  tempUrls,
  setTempUrls,
  isLoading,
  isHide,
  setIsLoading,
  setIsHide,
  setWidthResponsive,
  reportUrls,
}: any) => {
  const { t } = useTranslation();
  const { user, toggleSideBar } = useUserData();
  const themeUi = user?.user?.theme_ui;
  const location = useLocation();
  const navigate = useNavigate();
  const mdm = useSelector((state: RootState) => state.mdm);
  const dispatch = useDispatch();
  const [left, setLeft] = useState(0);
  const [tooltipPosition, setTooltipPosition] = useState<"up" | "down">("down");
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [tooltipMaxHeight, setTooltipMaxHeight] = useState<string>("");


 
  const { handleDownloadMTOVF, handleDownloadVF } = useDownloadHandler();
 
  const resetState = () => {
    dispatch(RESET_STATE());
    dispatch(RESET_MTO_STATE());
  };
 
  
  const calculateTooltipHeight = () => {
    const tooltipElement = tooltipRef.current;
    if (!tooltipElement) return;
  
    const rect = tooltipElement.getBoundingClientRect();
    setLeft(rect.width);
  
    const viewportHeight = window.innerHeight;
    const spaceBelow = viewportHeight - rect.bottom - 10;
    const spaceAbove = rect.top - 10;
  
    const desiredHeight = ITEM_HEIGHT * MIN_VISIBLE_ITEMS;
  
    let maxHeight;
    let position: "up" | "down";
  
    if (spaceBelow < desiredHeight && spaceAbove > spaceBelow) {
      position = "up";
      const effectiveMax = Math.min(spaceAbove, 300); 
      maxHeight = effectiveMax > desiredHeight + 60 ? effectiveMax : Math.min(spaceAbove, 500, desiredHeight);
    } else {
      position = "down";
      maxHeight = Math.min(spaceBelow, 500);
      if (maxHeight < desiredHeight) maxHeight = desiredHeight;
    }
    setTooltipMaxHeight(`${maxHeight}px`);
    setTooltipPosition(position);
  };
  
 
  useLayoutEffect(() => {
    calculateTooltipHeight();
    window.addEventListener("resize", calculateTooltipHeight);
    return () => {
      window.removeEventListener("resize", calculateTooltipHeight);
    };
  }, []);
 
  const handleTooltipClick = async (
    url: string,
    isMTO: boolean,
    downloadName?: any
  ) => {
    if (reportUrls.includes(url)) {
      setTempUrls([...tempUrls].concat(url));
      setIsLoading(true);
      if (isMTO) {
        await handleDownloadMTOVF(url, downloadName);
      } else {
        await handleDownloadVF(url, downloadName);
      }
      setIsLoading(false);
      const tempArr = tempUrls.filter((tempUrl: string) => tempUrl !== url);
      setTempUrls([...tempArr]);
    } else {
      navigateWithPrompt(() => {
        navigate(url, { replace: true });
        if (isHide) {
          setWidthResponsive({ widthLeft: "0%", widthRight: "95%" });
        }
        setIsHide(false);
        toggleSideBar(false);
      }, url, mdm, resetState);
    }
  };
 
  const getNestedChildren = (children: Array<any>): any => {
    const stack = [...children];
    const result = [];
    while (stack.length > 0) {
      const current = stack.pop();
      if (current.child) {
        stack.push(...current.child);
      } else {
        result.push(current);
      }
    }
    return result.reverse();
  };
 
  const renderToolTipContent = (items: any): any => {
    const result = getNestedChildren(items.child);
    return result.map((itemChild: any, index: number) => {
      if (
        user.url_permission.includes(itemChild.url) ||
        reportUrls.includes(itemChild.url)
      ) {
        return (
          <TooltipContent
            key={index}
            action={itemChild.url === location.pathname}
            themeUi={themeUi}
            onClick={() =>
              handleTooltipClick(
                itemChild.url,
                itemChild.isMTO,
                itemChild.downloadName
              )
            }
          >
            {t(itemChild.name) || itemChild.name}
            {itemChild.url !== location.pathname && (
              <SCIcon
                src={
                  isLoading && tempUrls.includes(itemChild.url)
                    ? "/assets/img/nav/loader.svg"
                    : itemChild.imgHover
                    ? itemChild.imgHover
                    : "/assets/img/nav/arrow_down.svg"
                }
                alt="arrow"
              />
            )}
          </TooltipContent>
        );
      }
    });
  };
 
  return (
    <div ref={tooltipRef}>
      <WrapToolTip left={left}>
        <Tooltip
          id={item.name}
          place="right"
          className="tooltip_list"
          noArrow
          isOpen
        >
          <TooltipContainer
            style={{
              maxHeight: tooltipMaxHeight,
              top: tooltipPosition === "down" ? "0" : "auto",
              bottom: tooltipPosition === "up" ? '-30px': "auto",
              background: 'white',
              minWidth: '230px',
              width: "fit-content",
              
            }}
          >
            <TooltipTitle>{t(item.name)}</TooltipTitle>
              <div style={{ overflowY: "auto", maxHeight: `calc(${tooltipMaxHeight} - 48px)` }}
              className="custom-scrollbar"
              >
              {renderToolTipContent(item)}
            </div>
          </TooltipContainer>
        </Tooltip>
      </WrapToolTip>
    </div>
  );
};
 
export default MenuToolTip;
 