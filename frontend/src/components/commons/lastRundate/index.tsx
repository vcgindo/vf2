// src/components/LastRunDateComponent.tsx
import React from 'react';
import { Skeleton } from '../styled';
import { LastRunDate,LastRunDateHeader } from '../../../VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/BPR/styles';

interface LastRunDateComponentProps {
  lastRunDate: string;
}

const LastRunDateComponent: React.FC<LastRunDateComponentProps> = ({ lastRunDate }) => {
  const demoLabel = process.env.REACT_APP_DEMO_MODE === 'true'
    ? 'Synthetic demo · Published snapshot'
    : null;

  return (
    <LastRunDate>
      {lastRunDate === "Loading" ? (
        <Skeleton style={{ height: 30, width: 150 }} />
      ) : (
        <LastRunDateHeader>
          {lastRunDate}{demoLabel ? ` · ${demoLabel}` : ''}
        </LastRunDateHeader>
      )}
    </LastRunDate>
  );
};

export default LastRunDateComponent;
