import { ButtonFloat } from "../../../components";
import { FileName, FilePanel, HeaderText } from "./style";

interface RightSectionFilePanelProps {
  img?: string;
  imgStyles?: React.CSSProperties;
  btnIcon: string;
  iconStyles: React.CSSProperties;
  text: string;
  onClick: () => void;
  disabled?: boolean;
}

function RightSectionFilePanel({
  img,
  imgStyles,
  btnIcon,
  iconStyles,
  text,
  onClick
}: RightSectionFilePanelProps) {
  return (
    <FilePanel onClick={onClick}>
      <FileName>
        <img src={img} alt="file" style={imgStyles} />
        <HeaderText fontSize="1.6rem" fontWeight="500">
          {text}
        </HeaderText>
      </FileName>
      <ButtonFloat
        icon={btnIcon}
        text=""
        onClick={onClick}
        styles={{
          width: "5rem",
          padding: "0.4rem 0.8rem",
          display: "grid",
          placeItems: "center",
        }}
        iconStyles={iconStyles}
      />
    </FilePanel>
  );
}

export default RightSectionFilePanel;
