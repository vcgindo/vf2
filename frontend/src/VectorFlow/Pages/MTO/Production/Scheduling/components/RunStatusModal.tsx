import React, { useState } from "react";
import { useUserData } from "../../../../../../context";
import VFButton from "../../../../../../components/VectorFLOW/commons/VFButton";
import VFButtonOutline from "../../../../../../components/VectorFLOW/commons/VFButtonOutline";
import { format } from "date-fns";
import { CloseButton, DateTimeWrapper, FooterWrapper, ImageWrapper, ModalHeader, ModalWrapper, ProgressContainer, ProgressFill, ProgressMessage, ProgressWrapper } from "./RunStatusModalStyles";



const RunStatusModal = ({
  runStatus,
  closeModal,
  message = "Run Failed",
  goTofinalResult,
}: any) => {
  const themeUi = useUserData().user.user.themeUi;
  
  const [isAbortConfirm, setIsAbortConfirm] = useState(false);
  const progressModal = () => {

    if (isAbortConfirm) {
      return (
        <ModalWrapper style={{ width: "40vw" }}>
          <ModalHeader>
            <CloseButton
              onClick={() => {
                setIsAbortConfirm(false);
              }}
            >
              ✕
            </CloseButton>
          </ModalHeader>
          <p style={{ padding: "30px 20px 30px 20px", fontSize: "1.4rem" }}>
            Are you sure you want to abort the process? The run process will
            stop and the file execution will be terminated.
          </p>
          <FooterWrapper style={{justifyContent: 'center', gap: '12px'}}>
            <VFButtonOutline
              style={{
                height: "3.2rem",
                fontSize: "1.25rem",
                borderColor: "#b52670",
                color: "#b52670"
              }}
              themeUi={themeUi}
              onClick={() => {
                setIsAbortConfirm(false);
              }}
            >
              No
            </VFButtonOutline>
            <VFButton
              style={{ height: "3.2rem", fontSize: "1.25rem" }}
              themeUi={themeUi}
              onClick={() => {
                setIsAbortConfirm(false);
                closeModal(true);
              }}
            >
              Yes
            </VFButton>
          </FooterWrapper>
        </ModalWrapper>
      );
    }
    return (
      <ModalWrapper style={{width: '58vw'}}>
        <ImageWrapper src={"/assets/img/scheduling/run-in-progress.svg"} />
        <ProgressWrapper>
          <ProgressContainer>
            <ProgressFill value={(isNaN(runStatus.progress.split('%')[0]))?0: Math.max(+runStatus.progress.split('%')[0],8)}>{runStatus.progress}</ProgressFill>
          </ProgressContainer>
          <ProgressMessage>{runStatus.current_step}...</ProgressMessage>
        </ProgressWrapper>
        <FooterWrapper>
          <DateTimeWrapper>
            <img
              src="/assets/img/scheduling/calendar-date.svg"
              alt="Calendar Icon"
              style={{ width: "16px", height: "16px" }}
            />
            <p>
              <strong>

              Run Start Time:{" "}
              </strong>
              {format(
                new Date(runStatus.started_at).toString(),
                "dd MMM yyyy, hh:mm a"
              )}  by {runStatus.triggered_by_username}
            </p>
          </DateTimeWrapper>

          {/* Todo: uncomment after abort implementation on backend  */}
          {/* <VFButton
            style={{
              display: "flex",
              gap: "8px",
              fontSize: "1.2rem",
              justifyContent: "center",
              alignItems: "center",
              height: "fit-content",
              padding: "8px 18px",
              width: "fit-content",
            }}
            onClick={() => {
              setIsAbortConfirm(true);
            }}
            themeUi={themeUi}
          >
            <img
              src="/assets/img/scheduling/Abort.svg"
              alt="Abort Icon"
              style={{ width: "16px", height: "16px" }}
            />
            <p>Abort</p>
          </VFButton> */}
        </FooterWrapper>
      </ModalWrapper>
    );
  };

  const progressCompletedModal = () => {
    return (
      <ModalWrapper style={{width: '58vw'}}>
        <ModalHeader>
          <CloseButton onClick={closeModal}>✕</CloseButton>
        </ModalHeader>
        <ImageWrapper style={{height: '38vh'}} src={"/assets/img/scheduling/run-complete.svg"} />
        <ProgressContainer>
            <ProgressFill value={(isNaN(runStatus.progress.split('%')[0]))?0: Math.max(+runStatus.progress.split('%')[0],8)}>{runStatus.progress}</ProgressFill>
          </ProgressContainer>
        <ProgressMessage style={{paddingBottom: '10px'}}>
          {"Run Completed Successfully"}
        </ProgressMessage>
        <FooterWrapper>
          <DateTimeWrapper>
            <img
              src="/assets/img/scheduling/calendar-date.svg"
              alt="Calendar Icon"
              style={{ width: "16px", height: "16px" }}
            />
            <p><strong>
              Run Start Time: &nbsp;
              </strong>
               {format(new Date(runStatus.started_at), "dd MMM yyyy, hh:mm a")} by {runStatus.triggered_by_username}</p>
          </DateTimeWrapper>
          <DateTimeWrapper>
            <img
              src="/assets/img/scheduling/calendar-date.svg"
              alt="Calendar Icon"
              style={{ width: "16px", height: "16px" }}
            />
            <p>
              <strong>
              Run End Time: &nbsp;
              </strong>
              {format(new Date(runStatus.ended_at), "dd MMM yyyy, hh:mm a")}</p>
          </DateTimeWrapper>
          <VFButton
            style={{
              display: "flex",
              gap: "8px",
              fontSize: "1.2rem",
              justifyContent: "center",
              alignItems: "center",
              height: "fit-content",
              padding: "8px 18px",
              width: "fit-content",
            }}
            onClick={()=>{goTofinalResult();closeModal();}}
            themeUi={themeUi}
          >
            <p>Go To Final Result</p>
          </VFButton>
        </FooterWrapper>
      </ModalWrapper>
    );
  };

  const progressAbortedModal = () => {
    return (
      <ModalWrapper style={{width: '55vw'}}>
        <ModalHeader>
          <CloseButton onClick={closeModal}>✕</CloseButton>
        </ModalHeader>
        <ImageWrapper src={"/assets/img/scheduling/run-aborted.svg"} />
        <ProgressMessage style={{ fontSize: "1.3rem", paddingBottom: "15px" }}>
          {message}
        </ProgressMessage>
        <FooterWrapper>
          <DateTimeWrapper>
            <img
              src="/assets/img/scheduling/calendar-date.svg"
              alt="Calendar Icon"
              style={{ width: "16px", height: "16px" }}
            />
            <p><strong>
              Run Start Time: &nbsp;
              </strong>
               {format(new Date(runStatus.started_at), "dd MMM yyyy, hh:mm a")}</p>
          </DateTimeWrapper>
          <DateTimeWrapper>
            <img
              src="/assets/img/scheduling/calendar-date.svg"
              alt="Calendar Icon"
              style={{ width: "16px", height: "16px" }}
            />
            <p>
              <strong>
                Run Abort Time: &nbsp;
                </strong>
                 {format(new Date(runStatus.ended_at), "dd MMM yyyy, hh:mm a")} by {runStatus.triggered_by_username}</p>

          </DateTimeWrapper>
          <VFButton
            style={{
              display: "flex",
              gap: "8px",
              fontSize: "1.2rem",
              justifyContent: "center",
              alignItems: "center",
              height: "fit-content",
              padding: "8px 18px",
              width: "fit-content",
            }}
            onClick={()=>{closeModal();}}
            themeUi={themeUi}
          >
            <p>Go Back</p>
          </VFButton>
        </FooterWrapper>
      </ModalWrapper>
    );
  };
  const progressFailedModal = () => {
    return (
      <ModalWrapper style={{width: "65vw"}}>
        <ModalHeader>
          <CloseButton onClick={closeModal}>✕</CloseButton>
        </ModalHeader>
        <ImageWrapper src={"/assets/img/scheduling/run-failed.svg"} />

        <ProgressMessage style={{ fontSize: "1.3rem", paddingBottom: "15px" }}>
          {message}
        </ProgressMessage>
        <FooterWrapper>
          <DateTimeWrapper>
            <img
              src="/assets/img/scheduling/calendar-date.svg"
              alt="Calendar Icon"
              style={{ width: "16px", height: "16px" }}
            />
            <p><strong>
              Run Start Time:  
              </strong>&nbsp;
              {format(new Date(runStatus.started_at), "dd MMM yyyy, hh:mm a")}  by {runStatus.triggered_by_username}</p>
          </DateTimeWrapper>
          <DateTimeWrapper>
            <img
              src="/assets/img/scheduling/calendar-date.svg"
              alt="Calendar Icon"
              style={{ width: "16px", height: "16px" }}
            />
            <p>
              <strong>

              Run Failed Time:
              &nbsp;
              </strong>
               {format(new Date(runStatus.ended_at), "dd MMM yyyy, hh:mm a")}</p>
          </DateTimeWrapper>
          <VFButtonOutline
            style={{
              display: "flex",
              gap: "8px",
              fontSize: "1.2rem",
              justifyContent: "center",
              alignItems: "center",
              height: "fit-content",
              padding: "8px 18px",
              width: "fit-content",
              borderColor: "#b52670",
              color: "#b52670",
            }}
            onClick={goTofinalResult}
            themeUi={themeUi}
          >
            Download Error File
          </VFButtonOutline>
          <VFButton
            style={{
              display: "flex",
              gap: "8px",
              fontSize: "1.2rem",
              justifyContent: "center",
              alignItems: "center",
              height: "fit-content",
              padding: "8px 18px",
              width: "fit-content",
            }}
            onClick={()=>{closeModal();}}
            themeUi={themeUi}
          >
            <p>Go Back</p>
          </VFButton>
        </FooterWrapper>
      </ModalWrapper>
    );
  };
  const progressFailedToFetch = () => {
    return (
      <ModalWrapper style={{width: "50vw"}}>
        <ImageWrapper src={"/assets/img/scheduling/run-failed.svg"} />
        <ProgressMessage style={{ fontSize: "1.3rem", paddingBottom: "15px" }}>
          {"Failed to fetch the run status. Please refresh to try again."}
        </ProgressMessage>
        <div style={{display: 'flex', justifyContent: 'center', alignItems: 'center', width: '100%', paddingBottom: '20px'}}>
          <VFButton
            style={{
              display: "flex",
              gap: "8px",
              fontSize: "1.2rem",
              justifyContent: "center",
              alignItems: "center",
              height: "fit-content",
              padding: "8px 18px",
              width: "fit-content",
            }}
            onClick={()=>{window.location.reload()}}
            themeUi={themeUi}
          >
            <p>Refresh</p>
          </VFButton>
        </div>
      </ModalWrapper>
    );
  };

  switch (runStatus?.status) {
    case "RUNNING":
      return progressModal();
    case "SUCCESS":
      return progressCompletedModal();
    case "FAILED":
      return progressFailedModal();
    case "ABORT":
      return progressAbortedModal();
    case "PENDING":
      return null;
    case "FAILED_TO_FETCH":
      return progressFailedToFetch();
    default:
      return null;
  }
};

export default RunStatusModal;
