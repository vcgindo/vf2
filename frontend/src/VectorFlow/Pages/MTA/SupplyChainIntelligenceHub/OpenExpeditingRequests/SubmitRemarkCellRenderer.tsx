import { BPRRemarksCellRendererWrapper } from "../BPR/styles";
import { SubmitRemarkInputWrapper } from "./styles";

const SubmitRemarkCellRenderer = (params: any) => {
  return (
    <BPRRemarksCellRendererWrapper>
      <SubmitRemarkInputWrapper>
        {params.value ? params.value : params.data.remarks}
      </SubmitRemarkInputWrapper>
    </BPRRemarksCellRendererWrapper>
  );
};
export default SubmitRemarkCellRenderer;
