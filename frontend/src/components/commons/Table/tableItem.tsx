import * as Tab from "./style";
import CheckboxPendingRequest from "../Checkbox/CheckboxPendingRequest";
import Checkbox from "../Checkbox";
import ButtonOutlineCheck from "../ButtonOutlineCheck";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useUserData } from "../../../context";

const TableItem = (props: any) => {
  const { t } = useTranslation();
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
  const [checkButton, setCheckButton] = useState(false);
  const { item, index, listCheckAll, setListCheckAll } = props;
  const [listRequest, setListRequest] = useState([] as number[]);
  const checkAllTable = () => {
    setCheckButton(!checkButton);
    setListCheckAll(!listCheckAll, index);
  };
  const checkTable = (id: number) => {
    const i = listRequest.findIndex((i) => i === id);
    const temp: any = [...listRequest];
    if (i === -1) {
      setCheckButton(!checkButton);
      temp.push(id);
    } else {
      setCheckButton(!checkButton);
      temp.splice(i, 1);
    }
    setListRequest(temp);
  };

  useEffect(() => {
    const checkAll =
      listRequest.length ===
      item.list_items.filter((item: any) => item._type === null).length;

    setListCheckAll(checkAll, index);
  }, [listRequest]);

  useEffect(() => {
    if (!listCheckAll) {
      if (
        listRequest.length ===
        item.list_items.filter((item: any) => item._type === null).length
      ) {
        setListRequest([]);
      }
    } else {
      const temp = item.list_items
        .filter((item: any) => item._type === null)
        .map((i: any) => i.id);
      if (temp.length > 0) {
        setListRequest(temp);
      }
    }
  }, [listCheckAll]);

  const onAcceptTable = () => {
    const listAllAccept = item.list_items.length === listRequest.length;
    const tempNull = item.list_items
      .filter((item: any) => item._type === null)
      .map((i: any) => i.id);
    const resDataPause = tempNull.filter(
      (item: any) => !listRequest.includes(item)
    );
    props.onModalAccept("ACCEPTED", listRequest, resDataPause, listAllAccept);
  };
  const onPauseTable = () => {
    const listAllPause = item.list_items.length === listRequest.length;
    const tempNull = item.list_items
      .filter((item: any) => item._type === null)
      .map((i: any) => i.id);
    const listCountData = tempNull.filter(
      (item: any) => !listRequest.includes(item)
    );
    props.onModalPause("PAUSED", listRequest, listCountData, listAllPause);
  };

  const onRejectTable = () => {
    const listAllReject = item.list_items.length === listRequest.length;
    const tempNull = item.list_items
      .filter((item: any) => item._type === null)
      .map((i: any) => i.id);
    const listCountData = tempNull.filter(
      (item: any) => !listRequest.includes(item)
    );
    props.onModalReject("REJECTED", listRequest, listCountData, listAllReject);
  };

  const checkValueStatus = (item: any) => {
    switch (item._type) {
      case "ACCEPTED":
        return "3";
      case "PAUSED":
        return "2";
      case "REJECTED":
        return "-1";
      default:
        if (listRequest.includes(item.id)) {
          return "1";
        }
        return "0";
    }
  };
  const checkDisplayButtonCheck = useMemo(() => {
    const checkArray = item.list_items.filter(
      (item: any) => item._type === null
    );
    return checkArray.length > 0;
  }, [item.list_items]);
  return (
    <>
      <Tab.SCTableTab width="100%">
        <Tab.SCTableTr>
          <Tab.SCTableTh style={{ display: "flex", alignItems: "center" }}>
            <Tab.SCTableCheckbox>
              {checkDisplayButtonCheck ? (
                <Checkbox
                  defaultChecked={listCheckAll}
                  name="id"
                  value={item.id}
                  onChange={() => {
                    checkAllTable();
                  }}
                ></Checkbox>
              ) : (
                ""
              )}
            </Tab.SCTableCheckbox>
            {t("pendingISTRequests.table.itemCode")}
          </Tab.SCTableTh>
          <Tab.SCTableTh>
            {t("pendingISTRequests.table.quantity")}
          </Tab.SCTableTh>
          <Tab.SCTableTh>
            {t("pendingISTRequests.table.donorROSN")}
          </Tab.SCTableTh>
          <Tab.SCTableTh>{t("pendingISTRequests.table.PvPA")}</Tab.SCTableTh>
          <Tab.SCTableTh>
            {t("pendingISTRequests.table.donorLocation")}
          </Tab.SCTableTh>
          <Tab.SCTableTh>{t("pendingISTRequests.table.city")}</Tab.SCTableTh>
          <Tab.SCTableTh>
            {t("pendingISTRequests.table.locationCode")}
          </Tab.SCTableTh>
          <Tab.SCTableTh>
            {t("pendingISTRequests.table.locationType")}
          </Tab.SCTableTh>
          <Tab.SCTableTh>{t("pendingISTRequests.table.channel")}</Tab.SCTableTh>
          <Tab.SCTableTh>{t("pendingISTRequests.table.vfISTID")}</Tab.SCTableTh>
        </Tab.SCTableTr>
        {item.list_items.map((i: any) => (
          <Tab.SCTableTr key={i.id}>
            <Tab.SCTableTdItem
              style={{ display: "flex", alignItems: "center" }}
            >
              <Tab.SCTableCheckbox>
                <CheckboxPendingRequest
                  onChange={() => {
                    checkTable(i.id);
                  }}
                  valueStatus={checkValueStatus(i)}
                  name={i.id.toString()}
                />
              </Tab.SCTableCheckbox>{" "}
              <span>{i?.sku_label}</span>
            </Tab.SCTableTdItem>
            <Tab.SCTableTd>
              {String(i?.quantity_to_be_moved).padStart(2, "0")}
            </Tab.SCTableTd>
            <Tab.SCTableTd>
              {/* eslint-disable-next-line no-unsafe-optional-chaining */}
              {(i?.donor_rosn).toString().slice(0, 4)}
            </Tab.SCTableTd>
            <Tab.SCTableTd>
              <Tab.SCWrapPvPA>
                <Tab.SCValuePvPA value={i?.before_col}>
                  {i?.before_col}
                </Tab.SCValuePvPA>
                <Tab.SCLargerSign src="/assets/img/ist/PvPA.svg" alt="PvPA" />
                <Tab.SCValuePvPA value={i?.after_col}>
                  {i?.after_col}
                </Tab.SCValuePvPA>
              </Tab.SCWrapPvPA>
            </Tab.SCTableTd>
            <Tab.SCTableTd>{i?.donor_wh_name}</Tab.SCTableTd>
            <Tab.SCTableTd>{i?.donor_wh_city}</Tab.SCTableTd>
            <Tab.SCTableTd>{i?.donor_wh_code}</Tab.SCTableTd>
            <Tab.SCTableTd>{i?.donor_wh_type}</Tab.SCTableTd>
            <Tab.SCTableTd>{i?.donor_wh_subtype}</Tab.SCTableTd>
            <Tab.SCTableTd>{i?.vf_ist_id}</Tab.SCTableTd>
          </Tab.SCTableTr>
        ))}
      </Tab.SCTableTab>
      {item.list_items.length > 0 && checkDisplayButtonCheck ? (
        <Tab.SCButtonChecBox>
          <ButtonOutlineCheck
            styles={
              listRequest.length > 0 && checkDisplayButtonCheck
                ? {
                    background:
                      themeUi === "REGALBLAZE" ? "#C7810E" : "#820F4C",
                  }
                : { background: "#D8D8D8", pointerEvents: "none" }
            }
            icon="accept"
            text={t("pendingISTRequests.button.accept")}
            onChange={() => {
              onAcceptTable();
            }}
          />
          <ButtonOutlineCheck
            styles={
              listRequest.length > 0 && checkDisplayButtonCheck
                ? {}
                : { pointerEvents: "none" }
            }
            icon="pause"
            text={t("pendingISTRequests.button.pause")}
            onChange={() => {
              onPauseTable();
            }}
          />
          <ButtonOutlineCheck
            styles={
              listRequest.length > 0 && checkDisplayButtonCheck
                ? {}
                : { pointerEvents: "none" }
            }
            icon="deline"
            text={t("pendingISTRequests.button.reject")}
            onChange={() => {
              onRejectTable();
            }}
          />
        </Tab.SCButtonChecBox>
      ) : (
        ""
      )}
    </>
  );
};
export default TableItem;
