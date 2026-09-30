import React, { useEffect, useRef, useState } from "react";
import styled from "styled-components";

type VFModalCardProps = {
  openModal: boolean;
  children: React.ReactNode;
  parentSelector?: string; // CSS selector for your parent container
};

const Overlay = styled.div<{ left: number; width: number }>`
  position: fixed;
  top: 0;
  left: ${(props) => props.left}px;
  width: ${(props) => props.width+40}px;
  height: 100%;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  border-radius: 12px;

`;

const ModalCard = styled.div`
  background: white;
  border-radius: 12px;
  // width: 420px;
  // max-width: 90%;
  // height: 260px;
  height: fit-content;
  width: fit-content;
  // padding: 0 15px;
  box-shadow: 0px 8px 24px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
`;

const Content = styled.div`
  flex: 1;
  overflow-y: auto;
  border-radius: 12px;

`;

const VFOverlayModal: React.FC<VFModalCardProps> = ({
  openModal,
  children,
  parentSelector = "#main-content", // default selector for parent
}) => {
  const [dimensions, setDimensions] = useState({ left: 0, width: window.innerWidth });

  useEffect(() => {
    const parentEl = document.querySelector(parentSelector);
    if (!parentEl) return;

    const updatePosition = () => {
      const rect = parentEl.getBoundingClientRect();
      setDimensions({ left: rect.left, width: rect.width });
    };

    // Initial position
    updatePosition();

    // Listen to resize changes in parent
    const resizeObserver = new ResizeObserver(updatePosition);
    resizeObserver.observe(parentEl);

    // Also listen for window resize
    window.addEventListener("resize", updatePosition);

    // return () => {
    //   resizeObserver.disconnect();
    //   window.removeEventListener("resize", updatePosition);
    // };
  }, [parentSelector]);

  if (!openModal) return null;

  return (
    <Overlay
      left={dimensions.left}
      width={dimensions.width}
    >
      <ModalCard onClick={(e) => e.stopPropagation()}>
        <Content>{children}</Content>
      </ModalCard>
    </Overlay>
  );
};

export default VFOverlayModal;
