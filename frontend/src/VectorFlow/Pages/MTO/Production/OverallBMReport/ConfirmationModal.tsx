import React from 'react';
import VFModalCard from '../../../../../components/VectorFLOW/commons/VFModalCard';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (val: any, action: string) => void;
  title: string;
  message?: any;
  actionText: any; 
  orderCount: number; 
  shortCloseTracker?: any;
  completeCloseTracker?:any
}

const ConfirmationModal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  actionText,
  orderCount,
  shortCloseTracker,
  completeCloseTracker,
}) => {
  if (!isOpen) return null;

 
  const hasNoOrders = orderCount === 0;

  return (
    <VFModalCard
      openModal={isOpen}
      closeModal={onClose}
      headerText={title}
      headerIcon={""}
      closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"}
      paddingLeftAndRight={0}
      headerTextColor={"black"}
      backgroundColor={"f4f4f4"}
      data-testid="vfmultifilter-img"
    >
      <div style={{ padding: "10px 20px", maxWidth: "500px", margin: "0 auto" }}>
        <div
          style={{
            margin: "20px 0",
            textAlign: "center",
            fontSize: "16px",
            color: "#444",
            wordWrap: "break-word",
            overflowWrap: "break-word",
            lineHeight: "1.5",
          }}
        >
          {hasNoOrders ? (
            <p style={{ color: "#d9534f", fontWeight: "bold" }}>
              No MTO orders to close.
            </p>
          ) : (
            <>
              <p style={{ marginBottom: "10px" }}>{message}</p>
              {shortCloseTracker && completeCloseTracker ? (
                <p>
                  Are you sure you want to <strong>Short Close</strong> {shortCloseTracker} {shortCloseTracker === 1 ? "Order" : "Orders"} and{" "}
                  <strong>Complete Close</strong> {completeCloseTracker} {completeCloseTracker === 1 ? "Order" : "Orders"}?
                </p>
              ) : (
                typeof orderCount === "number" ? (
                  <p>
                    Are you sure you want to <strong>{actionText}</strong> {orderCount} {orderCount === 1 ? "Order" : "Orders"}?
                  </p>
                ) : (
                  <p>
                    Are you sure you want to <strong>{actionText}</strong> order with order id{" "}
                    {orderCount}?
                  </p>
                )
              )}
            </>
          )}
        </div>

        {/* Button Section */}
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: "10px",
            paddingRight: "10px",
          }}
        >
          <button
            onClick={onClose}
            style={{
              background: "#fff",
              color: "#555",
              border: "1px solid #ccc",
              borderRadius: "4px",
              padding: "8px 16px",
              cursor: "pointer",
            }}
          >
            {hasNoOrders ? "Close" : "Cancel"}
          </button>

          {!hasNoOrders && (
            <button
              onClick={() => {
                orderCount !== null &&
                  onConfirm(typeof orderCount === "number" ? "" : orderCount, actionText);
              }}
              style={{
                background: "#A50064",
                color: "#fff",
                border: "none",
                borderRadius: "4px",
                padding: "8px 16px",
                cursor: "pointer",
              }}
            >
              Confirm
            </button>
          )}
        </div>
      </div>
    </VFModalCard>
  );
};

export default ConfirmationModal;