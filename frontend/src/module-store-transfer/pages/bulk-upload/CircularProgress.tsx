import React from "react";
import {  Svg, Circle, Text } from "./style";

type CircularProgressProps = {
  size: number;
  progress: number; // 0 to 100
  strokeWidth?: number;
  color?: string;
  bgColor?: string;
};

const CircularProgress: React.FC<CircularProgressProps> = ({
  size,
  progress,
  strokeWidth = 10,
  color = "#bd2c84",
  bgColor = "#eee",
}) => {
  const center = size / 2;
  const radius = center - strokeWidth / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (progress / 100) * circumference;

  return (

      <Svg width={size} height={size}>
        <Circle
          cx={center}
          cy={center}
          r={radius}
          strokeWidth={strokeWidth}
          stroke={bgColor}
          fill="none"
        />
        <Circle
          cx={center}
          cy={center}
          r={radius}
          strokeWidth={strokeWidth}
          stroke={color}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${center} ${center})`}
        />
        <Text x="50%" y="50%" dy=".3em">{`${progress}%`}</Text>
      </Svg>

  );
};

export default CircularProgress;
