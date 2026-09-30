import { useState } from "react";
import CheckboxPendingRequest from "../Checkbox/CheckboxPendingRequest";
import Checkbox from "../Checkbox";
import ButtonOutlineCheck from "../ButtonOutlineCheck";
import * as Tab from "./style";
import { useTranslation } from "react-i18next";
const TableItem = (props: any) => {
  const { t } = useTranslation();
  const cell = [
    t("ISTForcedClosure.table.skuCode"),
    t("ISTForcedClosure.table.size"),
    t("ISTForcedClosure.table.quantity"),
    t("ISTForcedClosure.table.status"),
    t("ISTForcedClosure.table.type"),
    t("ISTForcedClosure.table.receiverLocation"),
    t("ISTForcedClosure.table.city"),
    t("ISTForcedClosure.table.channel"),
    t("ISTForcedClosure.table.vfISTID"),
  ];
  const [checkButton, setCheckButton] = useState(false);

  const {
    item,
    index,
    listCheckAll,
    setListCheckAll,
    onClickModalTerminal,
    checkColorAge,
    contactDetail,
    listRequest,
    setListRequest,
    information,
    themeUi,
  } = props;

  const checkAllTable = () => {
    setCheckButton(!checkButton);
    setListCheckAll(!listCheckAll, index);

    if (listCheckAll) {
      const temp = item.list_items.map((i: any) => i.id);
      const newData = listRequest.filter((item: any) => !temp.includes(item));
      setListRequest(newData);
    } else {
      const newListNotGit = item.list_items.filter(
        (item: any) => item.status !== "GIT"
      );
      const temp = newListNotGit.map((i: any) => i.id);
      if (temp.length > 0) {
        const data = filterDuplicateValues([...listRequest, ...temp]);
        setListRequest([...data]);
      }
    }
  };

  const filterDuplicateValues = (listData: any) => {
    const newListData = listData.filter((item: string, index: number) => {
      return listData.indexOf(item) == index;
    });

    return newListData;
  };

  const checkValueStatus = (item: any) => {
    if (listRequest.includes(item.id)) {
      return "1";
    }
    return "0";
  };

  const checkTable = (id: number) => {
    const i = listRequest.findIndex((i: any) => i === id);

    const temp: any = [...listRequest];
    if (i === -1) {
      setCheckButton(!checkButton);

      temp.push(id);
    } else {
      setCheckButton(!checkButton);
      setListCheckAll(false, index);
      temp.splice(i, 1);
    }
    setListRequest(temp);

    const isCheckAll = item.list_items
      .map((i: any) => i.id)
      .every((value: any) => temp.includes(value));
    setListCheckAll(isCheckAll, index);
  };

  const checkGit = item.list_items.find((item: any) => {
    if (item.status === "APPROVED" || item.status === "ACCEPT") {
      return true;
    }
  });

  const CheckBoxDisabled = () => {
    return (
      <input
        className="CheckboxPendingRequest_input"
        type="text"
        disabled={true}
      />
    );
  };

  const showStatus = (status: string) => {
    let color: any = "#000000";
    if (status === "APPROVED") {
      color = "#7D899B";
    } else if (status === "ACCEPT") {
      color = "#000000";
    } else if (status === "GIT") {
      color = "#464E5B";
    } else {
      color = "#000000";
    }

    return (
      <Tab.SCTableTd>
        <span style={{ color: color }}>{status}</span>
      </Tab.SCTableTd>
    );
  };

  return (
    <>
      <Tab.SCTableBox style={{ marginBottom: 30 }}>
        <Tab.SCTableInformation>
          <Tab.SCTableList>
            {information(item.product).map((item: any, index: number) => (
              <Tab.SCTableItem key={`table_${index}`}>
                <Tab.SCTableItemName>{item.name}</Tab.SCTableItemName>{" "}
                <Tab.SCTableItemValue>{item.value}</Tab.SCTableItemValue>
              </Tab.SCTableItem>
            ))}
          </Tab.SCTableList>
          <Tab.SCButtonContact
            onClick={() => contactDetail(item.product.donor_wh_code)}
            themeUi={themeUi}
          >
            <Tab.SCImgContact
              src={`/assets/img/forced/${themeUi === "REGALBLAZE" ? "contact_yellow" : "contact"
                }.svg`}
            />
            {t("ISTForcedClosure.contactDetails")}
          </Tab.SCButtonContact>
        </Tab.SCTableInformation>
        <Tab.SCTableTab width="100%">
          <Tab.SCTableTr>
            <Tab.SCTableThItem>
              <Tab.SCTableCheckbox>
                {checkGit ? (
                  <Checkbox
                    value={item.id}
                    defaultChecked={listCheckAll}
                    name="id"
                    onChange={() => {
                      checkAllTable();
                    }}
                  />
                ) : (
                  <CheckBoxDisabled />
                )}
              </Tab.SCTableCheckbox>
              <Tab.SCTextStyle>{t("ISTForcedClosure.age")}</Tab.SCTextStyle>
            </Tab.SCTableThItem>
            {cell.map((i: string) => (
              <Tab.SCTableTh>{i}</Tab.SCTableTh>
            ))}
          </Tab.SCTableTr>
          {item.list_items.map((i: any) => (
            <Tab.SCTableTr>
              <Tab.SCTableTdDay
                style={{ color: `${checkColorAge(i?.ageing)}` }}
              >
                {i?.status !== "GIT" ? (
                  <div style={{ display: "flex", alignItems: "center" }}>
                    <CheckboxPendingRequest
                      onChange={() => {
                        checkTable(i.id);
                      }}
                      valueStatus={checkValueStatus(i)}
                      name={i.id.toString()}
                    />
                    <p>{i?.ageing + " " + t("ISTForcedClosure.days")}</p>
                  </div>
                ) : (
                  <div style={{ display: "flex", alignItems: "center" }}>
                    <CheckBoxDisabled />
                    <p>{i?.ageing + " " + t("ISTForcedClosure.days")}</p>
                  </div>
                )}
              </Tab.SCTableTdDay>
              <Tab.SCTableTd>{i?.sku_code}</Tab.SCTableTd>
              <Tab.SCTableTd>{i?.variant}</Tab.SCTableTd>
              <Tab.SCTableTd>{i?.quantity_to_be_moved}</Tab.SCTableTd>
              {showStatus(i?.status)}
              <Tab.SCTableTd>
                {i?.product_hierarchy_1 + " | " + i?.product_hierarchy_2 + " | " + i?.product_hierarchy_3}
              </Tab.SCTableTd>
              <Tab.SCTableTd>{i?.receiver_wh_name}</Tab.SCTableTd>
              <Tab.SCTableTd>{i?.receiver_wh_city}</Tab.SCTableTd>
              <Tab.SCTableTd>{i?.receiver_wh_subtype}</Tab.SCTableTd>
              <Tab.SCTableTd>{i?.vf_ist_id}</Tab.SCTableTd>
            </Tab.SCTableTr>
          ))}
        </Tab.SCTableTab>
        <Tab.SCButtonChecBox>
          <ButtonOutlineCheck
            styles={true}
            icon="deline"
            text={t("ISTForcedClosure.terminate")}
            onChange={() => onClickModalTerminal(index)}
          />
        </Tab.SCButtonChecBox>
      </Tab.SCTableBox>
    </>
  );
};

export default TableItem;
