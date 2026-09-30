import React from "react";
import { CustomTooltipProps } from "@ag-grid-community/react";
import styled from "styled-components";

const getTagStyles = (tag: string) => {
  if (!tag) {
    return { arrow: "#cccccc", bg: "#fff", text: "#000", border: "none" };
  }

  const lower = tag.toLowerCase();
  if (lower === "past scheduling") {
    return { arrow: "#E53F3F", bg: "#E53F3F", text: "#2F2B2B", border: "none" };
  }
  if (lower === "within scheduling") {
    return { arrow: "#A8A8A8", bg: "#A8A8A8", text: "#2F2B2B", border: "none" };
  }
  if (lower === "beyond scheduling") {
    return { arrow: "#f5f5f0", bg: "#f5f5f0", text: "#2F2B2B", border: "none" };
  }
  return { arrow: "#c1c1c1", bg: "#fff", text: "#111", border: "none" };
};

const TooltipWrapper = styled.div`
  color: white;
  background-color: transparent;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;

`;

const TagWrapper = styled.div`
  display: flex;
  align-items: center;
`;

const TagArrow = styled.div<{ arrowcolor: string; bordercolor: string }>`
  width: 0;
  height: 0;
  border-top: 11px solid transparent;
  border-bottom: 11px solid transparent;
  border-right: 15px solid ${({ arrowcolor }) => arrowcolor};
  ${({ bordercolor }) =>
    bordercolor !== "none" &&
    `border-top: 1px solid ${bordercolor}; border-bottom: 1px solid ${bordercolor};`};
`;

const TagLabel = styled.div<{ bgcolor: string; textcolor: string; bordercolor: string }>`
  padding: 5px 12px;
  line-height: 1;
  min-width: 120px;
  background: ${({ bgcolor }) => bgcolor};
  color: ${({ textcolor }) => textcolor};
  font-weight: 500;
  border-radius: 0 4px 4px 0;
  border: ${({ bordercolor }) => bordercolor};
`;

const LoadTagTooltip: React.FC<CustomTooltipProps> = (props) => {
  const rawValue = props.value;
  const tags: string[] = Array.isArray(rawValue)
    ? rawValue
    : [rawValue].filter(Boolean);

  if (tags.length === 0) {
    return <TooltipWrapper>No tags</TooltipWrapper>;
  }

  return (
    <TooltipWrapper>
      {tags.map((tag, idx) => {
        const style = getTagStyles(tag);
        return (
          <TagWrapper key={idx}>
            <TagArrow arrowcolor={style.arrow} bordercolor={style.border} />
            <TagLabel
              bgcolor={style.bg}
              textcolor={style.text}
              bordercolor={style.border}
            >
              {tag}
            </TagLabel>
          </TagWrapper>
        );
      })}
    </TooltipWrapper>
  );
};

export default LoadTagTooltip;
