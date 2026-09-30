import React, { useCallback, useEffect, useState } from 'react'
import { CustomCellRendererProps } from '@ag-grid-community/react';
import { RowEvent } from '@ag-grid-community/core';
import { Icon } from '../InsightsAndTrends/DayWiseCoverage/style';


const DayWiseCoverageMap: any = {
    "NK": "No Kit Orders",
    "FK": "Full Kit Orders",
    "PK": "Partial Kit Orders"
}

const CustomGroupCellRenderer = (props: CustomCellRendererProps) => {
    const { node, value } = props;
    const [expanded, setExpanded] = useState(node.expanded);

    //if you want to have rows expanded initially
    useEffect(() => {
        const expandListener = (event: RowEvent) => setExpanded(event.node.expanded);

        node.addEventListener('expandedChanged', expandListener);

        return () => {
            node.removeEventListener('expandedChanged', expandListener);
        }
    }, []);

    const onClick = useCallback(() => node.setExpanded(!node.expanded), [node]);

    return (
        node.group ?
            <button data-testid='collapsable' style={{ zoom: '0.6', fontSize: "18px", background: "transparent", fontWeight: "bold" }} onClick={onClick}>
                {DayWiseCoverageMap[value] ? DayWiseCoverageMap[value] : value}&nbsp;({props.node.allChildrenCount})&nbsp;&nbsp;<Icon src={expanded ? "/assets/img/mto/dayWiseCoverage/arrow_down.svg" : "/assets/img/mto/dayWiseCoverage/arrow_right.svg"} />
            </button>
            :
            <button data-testid='collapsable' style={{ zoom: '0.6', width: "100%", background: "transparent", textAlign: "right", height: "100%" }} onClick={onClick}>
                <Icon src={expanded ? "/assets/img/mto/dayWiseCoverage/collapse.svg" : "/assets/img/mto/dayWiseCoverage/expand.svg"} />
            </button>
    )
}

export default CustomGroupCellRenderer