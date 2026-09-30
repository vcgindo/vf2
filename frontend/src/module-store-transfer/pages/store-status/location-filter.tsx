import { forwardRef, useEffect, useImperativeHandle, useState } from "react";
import { useTranslation } from "react-i18next";
import { LocationFilter } from "../../../components";
import { MainStore } from "../../../services/store-status/api";

export default forwardRef((props, ref) => {
  const { t } = useTranslation();
  const [valueFilterBrand, setValueFilterBrand] = useState<any>([]);
  const [valueFilterLocName, setValueFilterLocName] = useState<any>([]);
  const [valueFilterLocCode, setValueFilterLocCode] = useState<any>([]);
  const [valueFilterLocCluster, setValueFilterLocCluster] = useState<any>([]);
  const [valueFilterChannel, setValueFilterChannel] = useState<any>([]);

  const [listMapBrand, setListMapBrand] = useState<any>([]);
  const [listMapLocName, setListMapLocName] = useState<any>([]);
  const [listMapLocCode, setListMapLocCode] = useState<any>([]);
  const [listMapLocCluster, setListMapLocCluster] = useState<any>([]);
  const [listMapChannel, setListMapChannel] = useState<any>([]);
  const [filterLoading, setFilterLoading] = useState<boolean>(false);

  useEffect(() => {
    setFilterLoading(true);
    MainStore.getFilterLocationStore()
      .then((res: any) => {
        const dataStore = res?.data.data;
        const listMapBrand =
          dataStore?.specific_sales &&
          dataStore?.specific_sales?.map((item: any) => {
            return { label: item, value: item };
          });
        setListMapBrand(listMapBrand);
        const listMapLocName =
          dataStore?.wh_name &&
          dataStore?.wh_name.map((item: any) => {
            return { label: item, value: item };
          });
        setListMapLocName(listMapLocName);
        const listMapLocCode =
          dataStore?.wh_code &&
          dataStore?.wh_code.map((item: any) => {
            return { label: item, value: item };
          });
        setListMapLocCode(listMapLocCode);
        const listMapLocCluster =
          dataStore?.wh_location_group &&
          dataStore?.wh_location_group.map((item: any) => {
            return { label: item, value: item };
          });
        setListMapLocCluster(listMapLocCluster);
        const listMapChannel =
          dataStore?.wh_subtype &&
          dataStore?.wh_subtype.map((item: any) => {
            return { label: item, value: item };
          });
        setListMapChannel(listMapChannel);
      })
      .catch((err: any) => {
        console.log(err);
      })
      .finally(() => {
        setFilterLoading(false);
      });
  }, []);

  const locationFilter = [
    {
      icon: "/assets/img/ist/target.svg",
      placeholder: t("filter.location.placeholder.storeStatus.brand"),
      options: listMapBrand,
      value: valueFilterBrand,
      onChange: setValueFilterBrand,
    },
    {
      placeholder: t("filter.location.placeholder.storeStatus.locName"),
      options: listMapLocName,
      value: valueFilterLocName,
      onChange: setValueFilterLocName,
    },
    {
      placeholder: t("filter.location.placeholder.storeStatus.locCode"),
      options: listMapLocCode,
      value: valueFilterLocCode,
      onChange: setValueFilterLocCode,
    },
    {
      placeholder: t("filter.location.placeholder.storeStatus.locGrp"),
      options: listMapLocCluster,
      value: valueFilterLocCluster,
      onChange: setValueFilterLocCluster,
    },
    {
      placeholder: t("filter.location.placeholder.storeStatus.channel"),
      options: listMapChannel,
      value: valueFilterChannel,
      onChange: setValueFilterChannel,
    },
  ];

  useImperativeHandle(ref, () => ({
    getLocationFilterValue() {
      return getLocationFilterValue();
    },
    resetFilter() {
      resetFilter();
    },
  }));

  const resetFilter = () => {
    setValueFilterBrand([]);
    setValueFilterLocName([]);
    setValueFilterLocCode([]);
    setValueFilterLocCluster([]);
    setValueFilterChannel([]);
  };

  const getLocationFilterValue = () => {
    return {
      valueFilterBrand,
      valueFilterLocName,
      valueFilterLocCode,
      valueFilterLocCluster,
      valueFilterChannel,
    };
  };

  return (
    <LocationFilter
      locationFilter={locationFilter}
      width={20}
      loading={filterLoading}
    />
  );
});
