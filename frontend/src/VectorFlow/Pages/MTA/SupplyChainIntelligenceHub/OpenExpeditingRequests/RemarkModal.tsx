import { useUserData } from "../../../../../context"
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton"
import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard"
import { ButtonWrapper, RemarkDate, RemarkModalContentWrapper, RemarkModalRemarkCelLRenderer, RemarkModalTable, RemarkModalTableCell, RemarkModalTableHeader, RemarkModalTableHeaderContainer, RemarkModalTableRow, RemarkModalTableRowContainer, RemarkText } from "../../Logistics/InTransitWhereAbouts/styles"
import UserIcon from "../../Logistics/InTransitWhereAbouts/UserIcon"

interface RemarkModalProps {
  isOpen: boolean
  onClose: () => void
  data: any 
}

const RemarkModal = (props: RemarkModalProps) => {
  const { isOpen, onClose, data } = props
  const { user } = useUserData()
  const theme_ui = user.user.theme_ui

  const safeData = Array.isArray(data)
    ? data
    : typeof data === "string"
    ? JSON.parse(data)
    : data?.data && Array.isArray(data.data)
    ? data.data
    : []

  return (
    <VFModalCard
      openModal={isOpen}
      headerIcon="/assets/img/VectorFLOW/BPR/remark.svg"
      headerText="Remarks"
      closeIcon="/assets/img/VectorFLOW/NMS/close-white.svg"
      closeModal={onClose}
    >
      <RemarkModalContentWrapper>
        <RemarkModalTable className="custom-scrollbar">
          <RemarkModalTableHeaderContainer>
            <RemarkModalTableHeader style={{ textAlign: "center", paddingRight: "5px" }}>
              Name
            </RemarkModalTableHeader>
            <RemarkModalTableHeader>Remarks</RemarkModalTableHeader>
            <RemarkModalTableHeader>ETA</RemarkModalTableHeader>
          </RemarkModalTableHeaderContainer>

          <RemarkModalTableRowContainer>
            {(!safeData || safeData.length === 0) ? (
              <p style={{ textAlign: "center", height: 200 }}>No data to show</p>
            ) : (
              safeData.map((d: any, index: number) => (
                <RemarkModalTableRow
                  key={index}
                  style={{ borderTop: index === 0 ? "none" : "dashed 1px gray" }}
                >
                  <UserIcon data={d.UserName || d.UserId} />
                  <RemarkModalTableCell>
                    <RemarkModalRemarkCelLRenderer>
                      <RemarkText>{d.r}</RemarkText>
                      <RemarkDate>{d.rd}</RemarkDate>
                    </RemarkModalRemarkCelLRenderer>
                  </RemarkModalTableCell>
                  <RemarkModalTableCell>{d.eta}</RemarkModalTableCell>
                </RemarkModalTableRow>
              ))
            )}
          </RemarkModalTableRowContainer>
        </RemarkModalTable>

        <ButtonWrapper>
          <VFButton onClick={onClose} themeUi={theme_ui}>
            Go Back!
          </VFButton>
        </ButtonWrapper>
      </RemarkModalContentWrapper>
    </VFModalCard>
  )
}

export default RemarkModal