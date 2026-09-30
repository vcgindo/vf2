import { useState, useEffect, useRef } from "react";
import {
  SCBoxFilterSticky,
  SCBoxFilter,
  SCQuickFilters,
  SCBoxFilterButton,
  SCBoxFilterButtonFlex,
  SCExportAllBox,
  SCExportAllBoxSpan,
  SCExportAllBoxButton,
  SCButtonFilter,
  SCFilterBtn,
  SCResetFilterBtn,
  SCSearchText,
  SCIconLocation,
  SCQuickFiltersWrap,
} from "./styes";
import {
  ButtonOutlineStatus,
  VerticalPartitions,
  SelectInput,
  TableForced,
  Pagination,
  InputSearchList,
  ListItemInput,
} from "./../../../components/index";
import { useGetAegingData } from "../../../services/forced";
import Spinner from "../../../components/commons/Spinner";
import { Forced } from "../../../services/forced/api";
import { DEFAULT_PAGE_SIZE } from "../../constants";
import { useNavigate } from "react-router-dom";
import { notifyError } from "../../../helpers/notify";
import axios from "axios";
import { useTranslation } from "react-i18next";
import LcnFilter from "../../../components/layouts/LocationFilter/common-filter";
import PrdFilter from "../../../components/layouts/ProductFilter/common-filter";
import { useUserData } from "../../../context";

interface SearchText {
  value: any;
  text: string;
  icon: string;
  type: string;
  onChange: (e: any) => void;
}

const IstForced = () => {
  const { t } = useTranslation();
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
  const { data: dataAeging } = useGetAegingData();

  const listDataAeging = dataAeging?.data.data;

  const nameAPIGetID = "api/forced-closure/get-id";

  const [currentOption, setCurrentOption] = useState();
  const [inputText, setInputText] = useState("");
  const [dataTime, setDataTime] = useState();
  const [dataIdItem, setDataIdItem] = useState<any>();
  const [listIdItem, setListIdItem] = useState();
  const [isOpenListItem, setIsOpenListItem] = useState(false);

  const onclickDate = (e: any) => {
    setDataTime(e.target.value);
  };

  const ref = useRef<any>();

  const handleChangeSelect = (e: any) => {
    setCurrentOption(e.target.value);
  };

  useEffect(() => {
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleClickOutside = (event: any) => {
    if (ref.current && !ref.current.contains(event.target)) {
      setIsOpenListItem(false);
    }
  };

  const search = window.location.search;
  const paramsPage = new URLSearchParams(search);
  const [buttonAuto, setButtonAuto] = useState({ auto: false, manual: false });
  const [buttonStatus, setButtonStatus] = useState({
    acceptdonor: false,
    shipment: false,
    inTransit: false,
  });
  const [listStatusAuto, setListStatusAuto] = useState([] as string[]);
  const [pageCount, setPageCount] = useState<number>(1);
  const [page, setPage] = useState<number>(
    parseInt("" + paramsPage.get("page")) || 1
  );
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [listTable, SetListTable] = useState([]);
  const [listCheckAll, setListCheckAll] = useState([] as boolean[]);
  const [listStatus, setListStatus] = useState([] as string[]);

  const [executeFilter, setExecuteFilter] = useState<number>(
    new Date().getTime()
  );
  const productFilterRef = useRef<any>();
  const locationFilterRef = useRef<any>();

  const navigate = useNavigate();

  useEffect(() => {
    const valueFilter = valueParams();
    const data: object = {
      page,
      per_page: DEFAULT_PAGE_SIZE,
      ...valueFilter,
    };

    setIsLoading(true);
    Forced.GetProductForced(data)
      .then((res: any) => {
        const { data } = res;
        SetListTable(data.data);
        setPageCount(data.pagination.number_pages);
      })
      .catch((err) => {
        console.log("error", Error);
        notifyError(err.msg);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [executeFilter, page, dataIdItem, dataTime, currentOption]);

  const onChangeAuto = async (data: string) => {
    const dataTemp = listStatusAuto;
    let check = true;
    dataTemp.forEach((element, index) => {
      if (element === data) {
        dataTemp.splice(index, 1);
        check = false;
      }
    });
    if (check) {
      dataTemp.push(data);
    }
    setButtonAuto({
      auto: data.toLowerCase() === "auto" ? !buttonAuto.auto : buttonAuto.auto,
      manual:
        data.toLowerCase() === "manual"
          ? !buttonAuto.manual
          : buttonAuto.manual,
    });
    setListStatusAuto(dataTemp);
    setExecuteFilter(new Date().getTime());
  };

  const onChangeDonor = async (data: string) => {
    const dataTemp = listStatus;
    let check = true;

    dataTemp.forEach((element, index) => {
      if (element === data) {
        dataTemp.splice(index, 1);
        check = false;
      }
    });

    if (check) {
      dataTemp.push(data);
    }
    setButtonStatus({
      acceptdonor:
        data.toLowerCase() === "approved"
          ? !buttonStatus.acceptdonor
          : buttonStatus.acceptdonor,
      shipment:
        data.toLowerCase() === "accept"
          ? !buttonStatus.shipment
          : buttonStatus.shipment,
      inTransit:
        data.toLowerCase() === "git"
          ? !buttonStatus.inTransit
          : buttonStatus.inTransit,
    });

    setListStatus(dataTemp);
    setPage(1);
    setExecuteFilter(new Date().getTime());
  };

  const handleDownload = async (nameFile: string) => {
    const data = valueParams();

    const response = await Forced.getDataExcel(data)
      .then((res: any) => {
        return res;
      })
      .catch((err) => {
        notifyError(err.msg);
      });

    const blob = new Blob([response.data], { type: "text/csv;charset=utf-8;" });
    if (navigator.msSaveBlob) {
      // IE 10+
      navigator.msSaveBlob(blob, nameFile);
    } else {
      const link = document.createElement("a");
      if (link.download !== undefined) {
        // feature detection
        // Browsers that support HTML5 download attribute
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", nameFile);
        link.style.visibility = "hidden";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    }
  };

  const onFilter = () => {
    setPage(1);
    navigate(
      {
        pathname: "/ist-forced-closure",
        search: "?page=" + 1,
      },
      { replace: true }
    );
    setExecuteFilter(new Date().getTime());
  };

  const resetFilter = () => {
    productFilterRef.current?.resetFilter();

    locationFilterRef.current?.resetFilter();

    setExecuteFilter(new Date().getTime());
    setPage(1);
    navigate(
      {
        pathname: "/ist-forced-closure",
        search: "?page=" + 1,
      },
      { replace: true }
    );
  };

  const handleChangePage = (event: any) => {
    navigate(
      {
        pathname: "/ist-forced-closure",
        search: "?page=" + event,
      },
      { replace: true }
    );
    window.scrollTo({ top: 0 });
    setPage(event);
  };

  const TextInput = ({ value, text, type, icon, onChange }: SearchText) => {
    return (
      <div>
        <SCIconLocation className="icon_location" src={icon} />
        <SCSearchText>
          <input
            type={type}
            value={value}
            onChange={(e) => {
              onChange(e);
            }}
            placeholder={text}
          />
        </SCSearchText>
      </div>
    );
  };

  let typingTimer: any;
  const doneTypingInterval = 2000;
  const inputChangeText = (e: any) => {
    setInputText(e.target.value);

    if (e.target.value.length === 0) {
      setDataIdItem([]);
      setIsOpenListItem(false);
    }
    clearTimeout(typingTimer);
    typingTimer = setTimeout(async () => {
      if (e.target.value.length > 0) {
        const data = await axios({
          method: "get",
          url: nameAPIGetID,
          params: { str_id: e.target.value },
        });
        setIsOpenListItem(true);
        setListIdItem(data.data.data);
      }
    }, doneTypingInterval);
  };

  const onClickItem = (e: any) => {
    const data =
      e.target.textContent === "VF IST ID" ? [] : [e.target.textContent];
    setInputText(e.target.textContent);

    setDataIdItem(data);
    setIsOpenListItem(false);
    setPage(1);
    navigate(
      {
        pathname: "/ist-forced-closure",
        search: "?page=1",
      },
      { replace: true }
    );
  };

  const valueParams = () => {
    let valueCurrentOption: any = [];
    if (currentOption) {
      valueCurrentOption = currentOption === "Ageing" ? [] : [currentOption];
    }
    const { brand, subBrand, category, style, fit, launchPeriod } =
      // eslint-disable-next-line no-unsafe-optional-chaining
      productFilterRef.current?.getProductFilterValue();
    const {
      istLocGrp,
      donorLocationName,
      donorLocationRegion,
      donorLocationSubType,
      transferPref,
      receiverLocationName,
      receiverLocationRegion,
      receiverLocationSubType,
      // eslint-disable-next-line no-unsafe-optional-chaining
    } = locationFilterRef.current?.getLocationFilterValue();

    return {
      ist_id: dataIdItem,
      ageing: valueCurrentOption,
      date_created: dataTime === "" ? null : dataTime,
      list_ist_type: listStatusAuto,
      list_status: listStatus,
      product_hierarchy_1: brand?.map((item: any) => item.value),
      product_hierarchy_2: subBrand?.map((item: any) => item.value),
      product_hierarchy_3: category.map((item: any) => item.value),
      generic_code: style.map((item: any) => item.value),
      product_hierarchy_4: fit.map((item: any) => item.value),
      wh_location_group: istLocGrp.map((item: any) => item.value),
      donor_wh_name: donorLocationName.map((item: any) => item.value),
      donor_wh_region: donorLocationRegion.map((item: any) => item.value),
      donor_wh_subtype: donorLocationSubType.map((item: any) => item.value),
      transfer_preference: transferPref.map((item: any) => item.value),
      receiver_wh_name: receiverLocationName.map((item: any) => item.value),
      receiver_wh_region: receiverLocationRegion.map((item: any) => item.value),
      receiver_wh_subtype: receiverLocationSubType.map(
        (item: any) => item.value
      ),
      launch_period: launchPeriod.map(
        (item: any) => item.value
      ),
    };
  };

  return (
    <>
      <SCBoxFilterSticky>
        <SCBoxFilter>
          <PrdFilter
            ref={productFilterRef}
            endpoint="/api/forced-closure/product-filter-list"
          />
          <LcnFilter
            ref={locationFilterRef}
            endpoint={{
              lcFilterList: "/api/forced-closure/location-filter-list",
            }}
          />
          <SCButtonFilter>
            <SCFilterBtn
              onClick={() => {
                onFilter();
              }}
              themeUi={themeUi}
            >
              {t("ISTForcedClosure.button.filter")}
            </SCFilterBtn>
            <SCResetFilterBtn onClick={resetFilter} themeUi={themeUi}>
              {t("ISTForcedClosure.button.resetFilter")}
            </SCResetFilterBtn>
          </SCButtonFilter>
        </SCBoxFilter>
        <SCQuickFilters>
          <SCQuickFiltersWrap>
            <div style={{ display: "flex", alignItems: "end", gap: "10px" }}>
              <InputSearchList
                placeholder={t("ISTForcedClosure.button.searchByISTID")}
                searchText={inputText}
                srcIcon="/assets/img/forced/stack.svg"
                handleChangeText={inputChangeText}
              />
              <TextInput
                value={dataTime}
                type="date"
                onChange={onclickDate}
                icon=""
                text={t("ISTForcedClosure.button.searchByISTDate")}
              />
            </div>
            {isOpenListItem && (
              <div ref={ref} style={{ position: "absolute" }}>
                <ListItemInput data={listIdItem} onClickItem={onClickItem} />
              </div>
            )}

            <VerticalPartitions height="55px" />

            <SCBoxFilterButton>
              <SCBoxFilterButtonFlex>
                <ButtonOutlineStatus
                  status={buttonAuto.auto}
                  icon=""
                  text={t("ISTForcedClosure.button.auto")}
                  onChange={async () => {
                    await onChangeAuto("Auto");
                  }}
                />
                <ButtonOutlineStatus
                  status={buttonAuto.manual}
                  icon=""
                  text={t("ISTForcedClosure.button.manual")}
                  onChange={async () => {
                    await onChangeAuto("Manual");
                  }}
                />
              </SCBoxFilterButtonFlex>
            </SCBoxFilterButton>

            <VerticalPartitions height="55px" />

            <SCBoxFilterButton>
              <SCBoxFilterButtonFlex>
                <ButtonOutlineStatus
                  status={buttonStatus.acceptdonor}
                  icon=""
                  text={t("ISTForcedClosure.button.pushedToSAP")}
                  onChange={async () => {
                    await onChangeDonor("APPROVED");
                  }}
                />
                <ButtonOutlineStatus
                  status={buttonStatus.shipment}
                  icon=""
                  text={t("ISTForcedClosure.button.readyToShip")}
                  onChange={async () => {
                    await onChangeDonor("ACCEPT");
                  }}
                />
                <ButtonOutlineStatus
                  status={buttonStatus.inTransit}
                  icon=""
                  text={t("ISTForcedClosure.button.inTransit")}
                  onChange={async () => {
                    await onChangeDonor("GIT");
                  }}
                />
                <SelectInput
                  name="ist"
                  value={currentOption}
                  handleChange={handleChangeSelect}
                  items={listDataAeging}
                  icon=""
                />
              </SCBoxFilterButtonFlex>
            </SCBoxFilterButton>

            <VerticalPartitions height="55px" />
          </SCQuickFiltersWrap>

          <SCBoxFilterButton>
            <SCExportAllBox>
              <SCExportAllBoxButton
                onClick={async () => {
                  await handleDownload("IST_forced_closure");
                }}
              >
                <img
                  src="/assets/img/forced/excel.png"
                  alt="and"
                  style={{ width: "26px" }}
                />
                <SCExportAllBoxSpan>
                  {t("ISTForcedClosure.button.exportAll")}
                </SCExportAllBoxSpan>
                <img src="/assets/img/forced/export.svg" alt="and" />
              </SCExportAllBoxButton>
            </SCExportAllBox>
          </SCBoxFilterButton>
        </SCQuickFilters>
      </SCBoxFilterSticky>
      {isLoading ? (
        <Spinner />
      ) : (
        <>
          <TableForced
            listCheckAll={listCheckAll}
            setListCheckAll={setListCheckAll}
            listTable={listTable}
            refetch={() => {
              setExecuteFilter(new Date().getTime());
            }}
          />
          {listTable.length > 0 && (
            <Pagination
              pageCount={pageCount}
              page={page}
              handleChangePerPage={handleChangePage}
              handleChangePage={handleChangePage}
            />
          )}
        </>
      )}
    </>
  );
};

export default IstForced;
