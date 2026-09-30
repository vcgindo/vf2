import * as Tab from "./style";
import { useState, useEffect } from "react";
import { Modal } from "../../index";
import { UsePutItemCodeChangeTye } from "../../../services/ist";
import { notifyError, notifySuccess } from "../../../helpers/notify";
import TableItem from "./tableItem";
import { t } from "i18next";

interface TableProps {
  data: any;
  listCheckAll: any;
  setListCheckAll: any;
  getData: () => void;
  listIdTable: any;
  isMoq: string;
  checkAllPage: boolean
}

const Table = ({
  data,
  listCheckAll,
  setListCheckAll,
  getData,
  listIdTable,
  isMoq,
  checkAllPage
}: TableProps) => {
  const [accept, setAccept] = useState("");
  const [isOpenAccept, setIsOpenAccept] = useState(false);
  const [isOpenReject, setIsOpenReject] = useState(false);
  const [isOpenPause, setIsOpenPause] = useState(false);

  const [listIdTableSingle, setListIdTableSingle] = useState([] as any);
  const [listIdTablePause, setListIdTablePause] = useState([] as any);

  useEffect(() => {    
    if (checkAllPage) {
      const temp = data?.map(() => true);
      setListCheckAll(temp);
    } else {
      const temp = data?.map(() => false);
      setListCheckAll(temp);
    }
  }, [data]);

  const { mutateAsync: putItemCodeChangeType } = UsePutItemCodeChangeTye();
  const onSave = () => {
    if (listIdTablePause.length > 0 && accept === "ACCEPTED") {
      const formDataPause = {
        ids: listIdTablePause,
        moq: isMoq,
        _type: "PAUSED",
      };

      putItemCodeChangeType(formDataPause, {
        onSuccess: (data: any) => {
          setListCheckAll([]);
          getData();
          setIsOpenAccept(false);
          setIsOpenReject(false);
          setIsOpenPause(false);
          if(data?.status === 400) {
            notifyError(data?.response?.msg)
          } else {
            notifySuccess(data?.data?.msg);
          }
        },
        onError: (error: any) => {
          notifyError(error.response.msg || error.message);
        },
      });
    }
    const formData = {
      ids: listIdTableSingle,
      moq: isMoq,
      _type: accept,
    };
    putItemCodeChangeType(formData, {
      onSuccess: (data: any) => {
        setListCheckAll([]);
        getData();
        setIsOpenAccept(false);
        setIsOpenReject(false);
        setIsOpenPause(false);
        if(data?.status === 400) {
          notifyError(data?.response?.msg)
        } else {
          notifySuccess(data?.data?.msg);
        }
        
      },
      onError: (error: any) => {        
        notifyError(error.response.msg || error.message);
      },
    });
  };

  const saveOne = (type: string, listId: any) => {
    const formData = {
      ids: listId,
      moq: isMoq,
      _type: type,
    };
    putItemCodeChangeType(formData, {
      onSuccess: (data: any) => {
        setListCheckAll([]);
        getData();
        if(data?.status === 400) {
          notifyError(data?.response?.msg)
        } else {
          notifySuccess(data.data.msg);
        }
        
      },
      onError: (data: any) => {
        notifyError(data.error);
      },
    });
  };

  const setCheckAllTable = (status: any, i: number) => {
    const temp = [...listCheckAll];
    temp[i] = status;
    setListCheckAll(temp);
  };

  const onCloseModal = () => {
    setIsOpenAccept(false);
    setIsOpenReject(false);
    setIsOpenPause(false);
  };

  const onModalAccept = (
    data: string,
    listItem: any,
    listCountData: any,
    listAllAccept: boolean
  ) => {
    if (
      (listCountData.length > 0 && !listAllAccept) ||
      (listItem.length > 1 && !listAllAccept)
    ) {
      setListIdTablePause(listCountData);
      setListIdTableSingle(listItem);
      setAccept(data);
      setIsOpenAccept(true);
    } else {
      saveOne(data, listItem);
    }
  };

  const onModalReject = (
    data: string,
    listItem: any,
    listCountData: any,
    listAllPause: boolean
  ) => {
    if (
      (listCountData.length > 0 && !listAllPause) ||
      (listItem.length > 1 && !listAllPause)
    ) {
      setListIdTableSingle(listItem);
      setAccept(data);
      setIsOpenReject(true);
    } else {
      saveOne(data, listItem);
    }
  };

  const onModalPause = (
    data: string,
    listItem: any,
    listCountData: any,
    listAllReject: boolean
  ) => {
    if (
      (listCountData.length > 0 && !listAllReject) ||
      (listItem.length > 1 && !listAllReject)
    ) {
      setListIdTableSingle(listItem);
      setAccept(data);
      setIsOpenPause(true);
    } else {
      saveOne(data, listItem);
    }
  };

  const dataTable =
    data &&
    data.map((item: any, idx: number) => (
      <Tab.SCTableBox key={idx} style={{ marginBottom: 30 }}>
        <Tab.SCTableInformation>
          <Tab.SCTableImages
            src="/assets/img/defaulimg.jpg"
            alt="logo"
            width={100}
          />
          <Tab.SCTableStyle>
            <Tab.SCTableStyleText>
              {t("pendingISTRequests.table.style")} - {item?.product?.generic_code}
              <Tab.SCTableStyleTextSpan>
                {item?.product?.product_hierarchy_1} | {item?.product?.product_hierarchy_2} |{" "}
                {item?.product?.product_hierarchy_3}
              </Tab.SCTableStyleTextSpan>
              <Tab.SCTableStyleTextSpan>
                {item?.product?.product_hierarchy_4} | <Tab.SCRupeeContainer><Tab.SCRupeeSign src="/assets/img/ist/rupee-icon.svg"/>{item?.product?.price}</Tab.SCRupeeContainer>
              </Tab.SCTableStyleTextSpan>
            </Tab.SCTableStyleText>
          </Tab.SCTableStyle>
          <Tab.SCTableList>
            <Tab.SCTableItem>
              <Tab.SCTableItemName>
                {t("pendingISTRequests.table.receiverROSN")}
              </Tab.SCTableItemName>
              <Tab.SCTableItemValue>
                {/* eslint-disable-next-line no-unsafe-optional-chaining */}
                {parseFloat(item?.product?.receiver_rosn).toFixed(2).toString()}
              </Tab.SCTableItemValue>
            </Tab.SCTableItem>
            <Tab.SCTableItem>
              <Tab.SCTableItemName>
                {t("pendingISTRequests.table.PvPA")}
              </Tab.SCTableItemName>
              <Tab.SCTableItemValue style={{display: "flex", alignItems: "center"}}>
                <Tab.SCValuePvPA value={item?.product?.before_col}>{item?.product?.before_col}</Tab.SCValuePvPA>
                <Tab.SCLargerSign src="/assets/img/ist/PvPA.svg" alt="PvPA" />
                <Tab.SCValuePvPA value={item?.product?.after_col}>{item?.product?.after_col}</Tab.SCValuePvPA>
              </Tab.SCTableItemValue>
            </Tab.SCTableItem>
            <Tab.SCTableItem>
              <Tab.SCTableItemName>
                {t("pendingISTRequests.table.receiverLocation")}
              </Tab.SCTableItemName>
              <Tab.SCTableItemValue>
                {item?.product?.receiver_wh_name}
              </Tab.SCTableItemValue>
            </Tab.SCTableItem>
            <Tab.SCTableItem>
              <Tab.SCTableItemName>
                {t("pendingISTRequests.table.city")}
              </Tab.SCTableItemName>
              <Tab.SCTableItemValue>
                {item?.product?.receiver_wh_city}
              </Tab.SCTableItemValue>
            </Tab.SCTableItem>
            <Tab.SCTableItem>
              <Tab.SCTableItemName>
                {t("pendingISTRequests.table.locationCode")}
              </Tab.SCTableItemName>
              <Tab.SCTableItemValue>
                {item?.product?.receiver_wh_code}
              </Tab.SCTableItemValue>
            </Tab.SCTableItem>
            <Tab.SCTableItem>
              <Tab.SCTableItemName>
                {t("pendingISTRequests.table.locationType")}
              </Tab.SCTableItemName>
              <Tab.SCTableItemValue>
                {item?.product?.receiver_wh_type}
              </Tab.SCTableItemValue>
            </Tab.SCTableItem>
          </Tab.SCTableList>
        </Tab.SCTableInformation>
        <TableItem
          item={item}
          setListCheckAll={setCheckAllTable}
          listCheckAll={listCheckAll[idx]}
          index={idx}
          onModalAccept={onModalAccept}
          onModalReject={onModalReject}
          onModalPause={onModalPause}
          listIdTable={listIdTable}
        />
      </Tab.SCTableBox>
    ));

  return (
    <>
      {dataTable}
      <Modal
        fileJson=""
        modalTitle={t("pendingISTRequests.modal.title")}
        modalContent={t("pendingISTRequests.modal.pause.content")}
        openModal={isOpenPause}
        closeModal={onCloseModal}
        onClickModal={() => {
          onSave();
        }}
        text={t("pendingISTRequests.modal.pause.button")}
      />
      <Modal
        fileJson=""
        modalTitle={t("pendingISTRequests.modal.title")}
        modalContent={t("pendingISTRequests.modal.reject.content")}
        openModal={isOpenReject}
        closeModal={onCloseModal}
        onClickModal={() => {
          onSave();
        }}
        text={t("pendingISTRequests.modal.reject.button")}
      />
      <Modal
        fileJson=""
        modalTitle={t("pendingISTRequests.modal.title")}
        modalContent={t("pendingISTRequests.modal.accept.content")}
        openModal={isOpenAccept}
        closeModal={onCloseModal}
        onClickModal={() => {
          onSave();
        }}
        text={t("pendingISTRequests.modal.accept.button")}
      />
    </>
  );
};
export default Table;
