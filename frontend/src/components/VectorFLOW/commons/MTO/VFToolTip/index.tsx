import React, { useRef, useEffect, useState } from "react";
// eslint-disable-next-line import/no-unresolved
import "./style.css"

interface VFToolTipProps {
  text: any;
  width?: number;
}

const VFToolTip: React.FC<VFToolTipProps> = ({
  text,
  width,
}) => {
  const tooltipRef = useRef<HTMLParagraphElement>(null);
  const [position, setPosition] = useState<'left' | 'center' | 'right'>('center');

  useEffect(() => {
    const checkPosition = () => {
      if (tooltipRef.current) {
        const rect = tooltipRef.current.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        
        // Checking if tooltip is goingg beyond right border
        if (rect.right > viewportWidth - 10) {
          setPosition('right');
        } 
        // Check if tooltip is goingg beyond left border
        else if (rect.left < 10) {
          setPosition('left');
        } 
        else {
          setPosition('center');
        }
      }
    };

    checkPosition();
    window.addEventListener('resize', checkPosition);
    return () => window.removeEventListener('resize', checkPosition);
  }, []);

  return (
    <p 
      ref={tooltipRef}
      className={`hover-text hover-text-${position}`} 
      style={{width: width }}
    >
      {text}
    </p>
  );
};

export default VFToolTip;
  
