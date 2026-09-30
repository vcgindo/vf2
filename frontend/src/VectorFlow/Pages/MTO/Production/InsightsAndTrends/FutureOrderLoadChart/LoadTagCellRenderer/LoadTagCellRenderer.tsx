import styled from "styled-components";
import React, { useState } from "react";

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
    return { arrow: "#E8E8E8", bg: "#E8E8E8", text: "#2F2B2B", border: "none" };
  }
  return { arrow: "#c1c1c1", bg: "#fff", text: "#111", border: "none" };
};

const TagArrow = styled.div<{ arrowcolor: string; bordercolor: string }>`
  width: 0;
  height: 0;
  border-top: 11px solid transparent;
  border-bottom: 11px solid transparent;
  border-right: 15px solid ${({ arrowcolor }) => arrowcolor};
  ${({ bordercolor }) => bordercolor !== "none" && `border-top: 1px solid ${bordercolor}; border-bottom: 1px solid ${bordercolor};`};
`;
 
const TagLabel = styled.div<{ bgcolor: string; textcolor: string; bordercolor: string }>`
  padding: 5px 12px;
  border-left: none;
  line-height: 1;
  height: 22px;
  min-width: 90px;
  display: inline-block;
  width:140px;
  background: ${({ bgcolor }) => bgcolor};
  color: ${({ textcolor }) => textcolor};
  font-weight: 500;
  border-radius: 0 4px 4px 0;
  border: ${({ bordercolor }) => bordercolor};
`;
 
const TagWrapper = styled.div`
  display: flex;
  align-items: center;
  height: 22px;
`;
 
const LoadTagCellRenderer = (params: any) => {
  const tags = Array.isArray(params.value) ? params.value : [params.value].filter(Boolean);
  const [hover, setHover] = useState(false);

  if (tags.length === 0) return null;

  return (
    <div
      style={{ display: "flex", alignItems: "center", position: "relative" }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      {/* First tag - main */}
      {tags[0] && (
        <TagWrapper style={{ zIndex: 2 }}>
          <TagArrow
            arrowcolor={getTagStyles(tags[0]).arrow}
            bordercolor={getTagStyles(tags[0]).border}
          />
          <TagLabel
            bgcolor={getTagStyles(tags[0]).bg}
            textcolor={getTagStyles(tags[0]).text}
            bordercolor={getTagStyles(tags[0]).border}
          >
            {tags[0]}
          </TagLabel>
        </TagWrapper>
      )}

      {/* Second tag - overlapped behind */}
      {tags[1] && (
        <TagWrapper
          style={{
            marginLeft: "-135px",// overlap,
            marginTop:'8px',
            // filter: "brightness(0.97)",
            zIndex: 1,
          }}
        >
          <TagArrow
            arrowcolor={getTagStyles(tags[1]).arrow}
            bordercolor={getTagStyles(tags[1]).border}
          />
          <TagLabel
            bgcolor={getTagStyles(tags[1]).bg}
            textcolor={getTagStyles(tags[1]).text}
            bordercolor={getTagStyles(tags[1]).border}
          >
            {tags[1]}
          </TagLabel>
        </TagWrapper>
      )}
     
    </div>
  );
};

export default LoadTagCellRenderer;
