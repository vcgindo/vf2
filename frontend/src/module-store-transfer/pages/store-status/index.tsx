import { useEffect, useRef, useState } from "react";
import {
  ButtonOutlineStatus,
  TableStore,
  Pagination,
} from "./../../../components/index";
import {
  SCQuickFiltersDistance,
  SCBoxFilter,
  SCQuickFilterBox,
  SCQuickFilterFlex,
  SCBoxHalfPart,
  SCButtonFilter,
  SCFilterBtn,
  SCResetFilterBtn,
  SCQuickFiltersText,
} from "./styles";
import { useGetFilterStoreStatus } from "../../../services/store-status";
import { useNavigate } from "react-router-dom";
import { DEFAULT_PAGE_SIZE } from "../../constants";
import Spinner from "../../../components/commons/Spinner";
import { useTranslation } from "react-i18next";
import LcnFilter from "./location-filter";
import { useUserData } from "../../../context";

const StoreStatus = () => {
  const { t } = useTranslation();
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
  const search = window.location.search;
  const paramsSearch = new URLSearchParams(search);
  const [page, setPage] = useState<number>(
    parseInt("" + paramsSearch.get("page")) || 1
  );
  const [buttonStatus, setButtonStatus] = useState({
    active: false,
    inActive: false,
  });
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const [filterLocation, setFilterLocation] = useState<any>({
    specific_sales: [],
    wh_name: [],
    wh_code: [],
    wh_location_group: [],
    wh_subtype: [],
    movement_status: null,
  });

  const navigate = useNavigate();
  const params = { ...filterLocation, page, per_page: DEFAULT_PAGE_SIZE };

  const { data: dataFetch, refetch } = useGetFilterStoreStatus(params);

  const dataStore = dataFetch?.data;

  const pageCount: number = dataStore?.pagination?.number_pages;

  useEffect(() => {
    const pathPage: any = search.split("=")[1];

    if (pageCount > 0 && parseInt(pathPage) > pageCount) {
      setIsLoading(true);
      setPage(pageCount);
      navigate(
        {
          pathname: "/store-status",
          search: "?page=" + pageCount,
        },
        { replace: true }
      );
      setTimeout(() => {
        setIsLoading(false);
      }, 500);
    }
  }, [pageCount]);

  const onChangeStatus = (action: string) => {
    setIsLoading(true);

    setButtonStatus({
      active:
        action.toLocaleLowerCase() === "active"
          ? !buttonStatus.active
          : buttonStatus.active,
      inActive:
        action.toLocaleLowerCase() === "inactive"
          ? !buttonStatus.inActive
          : buttonStatus.inActive,
    });

    const currentAction = action.toLocaleLowerCase();
    let resultStoreStatus: any;
    const { active, inActive } = buttonStatus;
    if (currentAction === "active") {
      if (!active) {
        resultStoreStatus = !inActive ? true : null;
      } else {
        resultStoreStatus = !inActive ? null : false;
      }
    } else {
      if (!inActive) {
        resultStoreStatus = !active ? false : null;
      } else {
        resultStoreStatus = !active ? null : true;
      }
    }

    const dataLocFilter = valueLocFilter();

    setFilterLocation({
      ...dataLocFilter,
      movement_status: resultStoreStatus,
    });

    setTimeout(() => {
      setIsLoading(false);
    }, 300);

    navigate(
      {
        pathname: "/store-status",
        search: "?page=1",
      },
      { replace: true }
    );
    setPage(1);
  };

  const handleFilter = () => {
    setIsLoading(true);

    const dataLocFilter = valueLocFilter();

    setFilterLocation({
      ...dataLocFilter,
    });
    setTimeout(() => {
      setIsLoading(false);
      navigate(
        {
          pathname: "/store-status",
          search: "?page=1",
        },
        { replace: true }
      );
      setPage(1);
    }, 300);
  };

  const locationFilterRef = useRef<any>();

  const handleResetFilter = () => {
    locationFilterRef.current?.resetFilter();

    setIsLoading(true);
    setButtonStatus({
      active: false,
      inActive: false,
    });

    setFilterLocation({
      specific_sales: [],
      wh_name: [],
      wh_code: [],
      wh_location_group: [],
      wh_subtype: [],
      movement_status: null,
    });
    setTimeout(() => {
      setIsLoading(false);
      setPage(1);
    }, 300);
    navigate(
      {
        pathname: "/store-status",
        search: "?page=" + 1,
      },
      { replace: true }
    );
  };

  const handleChangePage = (event: any) => {
    navigate(
      {
        pathname: "/store-status",
        search: "?page=" + event,
      },
      { replace: true }
    );
    window.scrollTo({ top: 0 });
    setPage(event);
  };

  const valueLocFilter = () => {
    const {
      valueFilterBrand,
      valueFilterLocName,
      valueFilterLocCode,
      valueFilterLocCluster,
      valueFilterChannel,
      // eslint-disable-next-line no-unsafe-optional-chaining
    } = locationFilterRef.current?.getLocationFilterValue();
    const valueBrand = valueFilterBrand?.map((item: any) => item.value);
    const valueLocName = valueFilterLocName?.map((item: any) => item.value);
    const valueLocCode = valueFilterLocCode.map((item: any) => item.value);
    const valueLocCluster = valueFilterLocCluster.map(
      (item: any) => item.value
    );
    const valueChannel = valueFilterChannel.map((item: any) => item.value);

    const dataLocFilter = {
      specific_sales: valueBrand.includes(
        t("filter.location.placeholder.storeStatus.brand")
      )
        ? []
        : valueBrand,
      wh_name: valueLocName.includes(
        t("filter.location.placeholder.storeStatus.locName")
      )
        ? []
        : valueLocName,
      wh_code: valueLocCode.includes(
        t("filter.location.placeholder.storeStatus.locCode")
      )
        ? []
        : valueLocCode,
      wh_location_group: valueLocCluster.includes(
        t("filter.location.placeholder.storeStatus.locGrp")
      )
        ? []
        : valueLocCluster,
      wh_subtype: valueChannel.includes(
        t("filter.location.placeholder.storeStatus.channel")
      )
        ? []
        : valueChannel,
      movement_status: filterLocation.movement_status,
    };

    return dataLocFilter;
  };

  return (
    <>
      <SCQuickFilterFlex>
        <SCBoxHalfPart>
          <SCBoxFilter>
            <LcnFilter ref={locationFilterRef} />
            <SCButtonFilter>
              <SCFilterBtn onClick={handleFilter} themeUi={themeUi}>
                {t("storeStatus.button.filter")}
              </SCFilterBtn>
              <SCResetFilterBtn onClick={handleResetFilter} themeUi={themeUi}>
                {t("storeStatus.button.resetFilter")}
              </SCResetFilterBtn>
            </SCButtonFilter>
          </SCBoxFilter>
        </SCBoxHalfPart>
        <SCQuickFilterBox>
          <SCQuickFiltersText>
            {t("storeStatus.quickFilter")} -
          </SCQuickFiltersText>
          <ButtonOutlineStatus
            status={buttonStatus.active}
            icon=""
            text={t("storeStatus.button.active")}
            onChange={() => {
              onChangeStatus("ACTIVE");
            }}
          />
          <ButtonOutlineStatus
            status={buttonStatus.inActive}
            icon=""
            text={t("storeStatus.button.inactive")}
            onChange={() => {
              onChangeStatus("INACTIVE");
            }}
          />
        </SCQuickFilterBox>
      </SCQuickFilterFlex>
      <SCQuickFiltersDistance></SCQuickFiltersDistance>

      {isLoading ? (
        <Spinner />
      ) : (
        <TableStore listTable={dataStore?.data} refetch={refetch} />
      )}
      <Pagination
        pageCount={pageCount}
        page={page}
        handleChangePerPage={handleChangePage}
        handleChangePage={handleChangePage}
      />
    </>
  );
};

export default StoreStatus;
