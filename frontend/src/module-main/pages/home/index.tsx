import { useState, useEffect, useRef } from "react";
import {
  Table,
  Pagination,
  ButtonOutlineStatus,
  Checkbox,
  VerticalPartitions,
  ButtonToggle3State,
  SelectAllPage,
} from "../../../components/index";
import { chooseThemeColor } from "../../../styles/global";
import {
  SCBoxFilter,
  SCQuickFilters,
  SCQuickFilterBox,
  SCQuickFiltersText,
  SCQuickAction,
  SCQuickActionSelect,
  SCQuickActionLabel,
  SCButtonFilter,
  SCQuickActionSelectInput,
  SCQuickActionButton,
  SCBoxFilterSticky,
  SCFilterBtn,
  SCResetFilterBtn,
  SCQuickFiltersWrap,
} from "./styles";
import { ISTService } from "../../../services/ist/api";
import Spinner from "../../../components/commons/Spinner/index";
import LoadingSpinner from "../../../components/commons/LoadingSpinner/index";
import { DEFAULT_PAGE_SIZE } from "../../constants";
import { UsePutItemCodeChangeTye } from "../../../services/ist";
import { notifyError, notifySuccess } from "../../../helpers/notify";
import { useNavigate } from "react-router-dom";
import { UseGetIstTotal } from "../../../module-main/services";
import { useTranslation } from "react-i18next";
import PrdFilter from "../../../components/layouts/ProductFilter/common-filter";
import LcnFilter from "../../../components/layouts/LocationFilter/common-filter";
import { useUserData } from "../../../context";

const Home = () => {
  const { t } = useTranslation();
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isLoadSpinner, setIsLoadingSpinner] = useState<boolean>(false);
  const [checkAllTable, setCheckAllTable] = useState(false);
  const [checkAllPage, setCheckAllPage] = useState<boolean>(false);
  const [listCheckAll, setListCheckAll] = useState([] as boolean[]);

  const navigate = useNavigate();
  const search = window.location.search;
  const params = new URLSearchParams(search);

  const [filterData, SetFilterData] = useState([]);
  const [page, setPage] = useState<number>(
    parseInt("" + params.get("page")) || 1
  );
  const [isMoq, setIsMoq] = useState<string>("All");
  const [listStatus, setListStatus] = useState([] as string[]);
  const [listStatusAuto, setListStatusAuto] = useState([] as string[]);
  const [pageCount, setPageCount] = useState<number>(1);
  const [inPage, setInPage] = useState<number>(0);
  const [total, setTotal] = useState<number>(0);

  const [buttonStatus, setButtonStatus] = useState({
    accepted: false,
    paused: false,
    rejected: false,
    auto: false,
    manual: false,
  });
  const [buttonAuto, setButtonAuto] = useState({ auto: false, manual: false });
  const [listIdTable, setListIdTable] = useState([]);
  const [listAllId, setListAllId] = useState([]);
  const [typeTable, setTypeTable] = useState("ACCEPTED");

  const { refetch } = UseGetIstTotal();

  const onChange = async (data: string) => {
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
    setListCheckAll([]);
    setButtonStatus({
      accepted:
        data.toLowerCase() === "accepted"
          ? !buttonStatus.accepted
          : buttonStatus.accepted,
      paused:
        data.toLowerCase() === "paused"
          ? !buttonStatus.paused
          : buttonStatus.paused,
      rejected:
        data.toLowerCase() === "rejected"
          ? !buttonStatus.rejected
          : buttonStatus.rejected,
      auto:
        data.toLowerCase() === "auto" ? !buttonStatus.auto : buttonStatus.auto,
      manual:
        data.toLowerCase() === "manual"
          ? !buttonStatus.manual
          : buttonStatus.manual,
    });

    setListStatus(dataTemp);
    setPage(1);
    setExecuteFilter(new Date().getTime());
  };

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
    setListCheckAll([]);
    setButtonAuto({
      auto: data.toLowerCase() === "auto" ? !buttonAuto.auto : buttonAuto.auto,
      manual:
        data.toLowerCase() === "manual"
          ? !buttonAuto.manual
          : buttonAuto.manual,
    });

    setListStatusAuto(dataTemp);
    setPage(1);
    setExecuteFilter(new Date().getTime());
  };

  const [executeFilter, setExecuteFilter] = useState<number>(
    new Date().getTime()
  );
  const productFilterRef = useRef<any>();
  const locationFilterRef = useRef<any>();

  const formFilter = () => {
    const { brand, subBrand, category, style, fit, launchPeriod } =
      // eslint-disable-next-line no-unsafe-optional-chaining
      productFilterRef.current?.getProductFilterValue();

    const valueBrand = brand.map((item: any) => item.value);
    const valueSubBrand = subBrand.map((item: any) => item.value);
    const valueCategory = category.map((item: any) => item.value);
    const valueStyle = style.map((item: any) => item.value);
    const valueFit = fit.map((item: any) => item.value);
    const valueLaunchPeriod = launchPeriod.map((item: any) => item.value);

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

    const valueIstLocGrp = istLocGrp.map((item: any) => item.value);
    const valueDonorLocationName = donorLocationName.map(
      (item: any) => item.value
    );
    const valueDonorLocationRegion = donorLocationRegion.map(
      (item: any) => item.value
    );
    const valueDonorLocationSubType = donorLocationSubType.map(
      (item: any) => item.value
    );
    const valueTransferPref = transferPref.map((item: any) => item.value);
    const valueReceiverLocationName = receiverLocationName.map(
      (item: any) => item.value
    );
    const valueReceiverLocationRegion = receiverLocationRegion.map(
      (item: any) => item.value
    );
    const valueReceiverLocationSubType = receiverLocationSubType.map(
      (item: any) => item.value
    );

    return {
      product_hierarchy_1: valueBrand,
      product_hierarchy_2: valueSubBrand,
      product_hierarchy_3: valueCategory,
      generic_code: valueStyle,
      product_hierarchy_4: valueFit,
      launch_period: valueLaunchPeriod,
      location_group: valueIstLocGrp,
      donor_wh_name: valueDonorLocationName,
      donor_wh_region: valueDonorLocationRegion,
      donor_wh_subtype: valueDonorLocationSubType,
      transfer_preference: valueTransferPref,
      receiver_wh_name: valueReceiverLocationName,
      receiver_wh_region: valueReceiverLocationRegion,
      receiver_wh_subtype: valueReceiverLocationSubType,
    };
  };

  useEffect(() => {
    const valueFilter = formFilter();

    const data: object = {
      page,
      is_moq: isMoq,
      per_page: DEFAULT_PAGE_SIZE,
      list_status: listStatus,
      list_ist_type: listStatusAuto,
      ...valueFilter,
    };

    setIsLoading(true);
    ISTService.getPendingFilter(data)
      .then((res: any) => {
        const { data } = res;

        refetch();
        setPageCount(data.pagination.number_pages);
        setInPage(data.pagination.in_page);
        setTotal(data.pagination.total);

        if (
          data.pagination.number_pages != 0 &&
          data.pagination.page > data.pagination.number_pages
        ) {
          setPage(data.pagination.number_pages);
          navigate(
            {
              pathname: "/",
              search: "?page=" + data.pagination.number_pages,
            },
            { replace: true }
          );
        }

        SetFilterData(data.data);
        const listTemp = data.data
          .map((item: any) => {
            return item.list_items
              .filter((item: any) => item._type === null)
              .map((i: any) => i.id);
          })
          .flat();
        setListAllId(listTemp);
      })
      .catch((err) => {
        console.log("error", Error);
        notifyError(err.msg);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [executeFilter, page, isMoq]);

  const onFilter = () => {
    setListCheckAll([]);
    setPage(1);
    navigate(
      {
        pathname: "/",
        search: "?page=" + 1,
      },
      { replace: true }
    );
    setExecuteFilter(new Date().getTime());
  };

  const handleChangePage = (event: any) => {
    setListCheckAll([]);
    navigate(
      {
        pathname: "/",
        search: "?page=" + event,
      },
      { replace: true }
    );
    window.scrollTo({ top: 0 });
    setPage(event);
  };

  const logState = (value: string) => {
    setListCheckAll([]);
    setIsMoq(value);
    setPage(1);
  };

  useEffect(() => {
    const temp = listCheckAll.includes(false);
    if (listCheckAll.length > 0) {
      setCheckAllTable(!temp);
    }
    if (temp) {
      setCheckAllPage(false);
    }
  }, [listCheckAll]);

  const onChangeCheckAll = () => {
    const listCheckAllClone = [...listCheckAll];
    if (checkAllTable) {
      const temp = listCheckAllClone.fill(false);
      setListCheckAll(temp);
      setListIdTable([]);
    } else {
      const temp = listCheckAllClone.fill(true);
      setListIdTable(listAllId);
      setListCheckAll(temp);
    }
    setCheckAllTable(!checkAllTable);
  };

  const { mutateAsync: putItemCodeChangeType } = UsePutItemCodeChangeTye();

  const onAction = async () => {
    setCheckAllTable(false);
    const valueFilter = formFilter();

    setIsLoadingSpinner(true);
    const dataId = checkAllPage ? [] : listIdTable;
    const formData = {
      ids: dataId,
      _type: typeTable,
      ist_filter: { moq: isMoq, ...valueFilter },
    };

    await putItemCodeChangeType(formData, {
      onSuccess: (data: any) => {
        if (data?.status === 400) {
          notifyError(data?.response?.msg);
        } else {
          notifySuccess(data?.data?.msg);
        }
        if (page === 1) {
          setPage(1);
        } else {
          setPage(page - 1);
        }
        setListCheckAll([]);
        setCheckAllPage(false);
        setExecuteFilter(new Date().getTime());
        setIsLoadingSpinner(false);
      },
      onError: (data: any) => {
        notifyError(data.response.msg || data.message);
        setIsLoadingSpinner(false);
      },
    });
  };

  const resetFilter = () => {
    setListCheckAll([]);
    productFilterRef.current?.resetFilter();

    locationFilterRef.current?.resetFilter();

    setExecuteFilter(new Date().getTime());
    navigate(
      {
        pathname: "/",
        search: "?page=" + 1,
      },
      { replace: true }
    );
    setPage(1);
  };

  const handleAction = () => {
    if (checkAllPage) {
      setListCheckAll([]);
    } else {
      setCheckAllPage(true);
    }
  };

  return (
    <>
      <SCBoxFilterSticky>
        <SCBoxFilter>
          <PrdFilter
            ref={productFilterRef}
            endpoint="/api/ist/pending/product-filter-list"
          />
          <LcnFilter
            ref={locationFilterRef}
            endpoint={{
              lcFilterList: "/api/ist/pending/location-filter-list",
            }}
          />
          <SCButtonFilter>
            <SCFilterBtn onClick={onFilter} themeUi={themeUi}>
              {t("pendingISTRequests.button.filter")}
            </SCFilterBtn>
            <SCResetFilterBtn onClick={resetFilter} themeUi={themeUi}>
              {t("pendingISTRequests.button.resetFilter")}
            </SCResetFilterBtn>
          </SCButtonFilter>
        </SCBoxFilter>
        <SCQuickFilters>
          <SCQuickFiltersWrap>
            <SCQuickAction>
              {listAllId.length > 0 ? (
                <Checkbox
                  name="action"
                  value="action"
                  onChange={onChangeCheckAll}
                  defaultChecked={checkAllTable}
                />
              ) : (
                ""
              )}
              <SCQuickActionSelect>
                <SCQuickActionLabel>
                  {t("pendingISTRequests.action.title")}
                </SCQuickActionLabel>
                <SCQuickActionSelectInput
                  onChange={(e) => {
                    setTypeTable(e.target.value);
                  }}
                >
                  <option value="ACCEPTED">
                    {t("pendingISTRequests.action.accept")}
                  </option>
                  <option value="PAUSED">
                    {t("pendingISTRequests.action.pause")}
                  </option>
                  <option value="REJECTED">
                    {t("pendingISTRequests.action.reject")}
                  </option>
                </SCQuickActionSelectInput>
              </SCQuickActionSelect>
            </SCQuickAction>
            <SCQuickFilterBox>
              <SCQuickActionButton
                style={
                  checkAllTable && listAllId.length > 0
                    ? { background: chooseThemeColor[themeUi].color5 }
                    : { background: "#D8D8D8", pointerEvents: "none" }
                }
                onClick={async () => {
                  await onAction();
                }}
              >
                <img src="/assets/img/ist/White-Arrow.svg" alt="filter" />
              </SCQuickActionButton>
            </SCQuickFilterBox>

            <VerticalPartitions />

            <SCQuickFilterBox>
              <SCQuickFiltersText>
                {t("pendingISTRequests.quickFilter.title")} -
              </SCQuickFiltersText>
              <ButtonOutlineStatus
                status={buttonStatus.accepted}
                icon=""
                text={t("pendingISTRequests.quickFilter.accepted")}
                onChange={async () => {
                  await onChange("ACCEPTED");
                }}
              />
              <ButtonOutlineStatus
                status={buttonStatus.paused}
                icon=""
                text={t("pendingISTRequests.quickFilter.paused")}
                onChange={async () => {
                  await onChange("PAUSED");
                }}
              />
              <ButtonOutlineStatus
                status={buttonStatus.rejected}
                icon=""
                text={t("pendingISTRequests.quickFilter.rejected")}
                onChange={async () => {
                  await onChange("REJECTED");
                }}
              />
            </SCQuickFilterBox>

            <VerticalPartitions />

            <SCQuickFilterBox>
              <ButtonOutlineStatus
                status={buttonAuto.auto}
                icon=""
                text={t("pendingISTRequests.quickFilter.auto")}
                onChange={async () => {
                  await onChangeAuto("Auto");
                }}
              />
              <ButtonOutlineStatus
                status={buttonAuto.manual}
                icon=""
                text={t("pendingISTRequests.quickFilter.manual")}
                onChange={async () => {
                  await onChangeAuto("Manual");
                }}
              />
            </SCQuickFilterBox>

            <VerticalPartitions />
          </SCQuickFiltersWrap>

          <ButtonToggle3State onClick={logState} />
        </SCQuickFilters>
      </SCBoxFilterSticky>

      {checkAllTable && (
        <SelectAllPage
          inPage={inPage}
          total={total}
          themeUi={themeUi}
          isCheckAllPage={checkAllPage}
          handleAction={handleAction}
        />
      )}

      {isLoading ? (
        <Spinner />
      ) : (
        <>
          <Table
            data={filterData}
            getData={() => {
              setExecuteFilter(new Date().getTime());
            }}
            listCheckAll={listCheckAll}
            setListCheckAll={setListCheckAll}
            listIdTable={listIdTable}
            isMoq={isMoq}
            checkAllPage={checkAllPage}
          />
          {filterData.length > 0 && (
            <Pagination
              pageCount={pageCount}
              page={page}
              handleChangePerPage={handleChangePage}
              handleChangePage={handleChangePage}
            />
          )}
        </>
      )}

      {isLoadSpinner && <LoadingSpinner />}
    </>
  );
};

export default Home;
