import { useCallback, useEffect, useState } from 'react'
import { CustomCellRendererProps } from '@ag-grid-community/react';
import { RowEvent } from '@ag-grid-community/core';
import { FlatIcon } from './styles';
import { useGetBombLevelData } from '../../../../../VectorFlow/Services/MTO/Production/DepartmentWiseBMReport';

const customCellRenderer = (props: CustomCellRendererProps) => {
//component not in use. Delete it later on 
const { mutateAsync: getBombLevelData, /*isLoading :BombDataLoading*/ } = useGetBombLevelData();
    const { node } = props;
    const [expanded, setExpanded] = useState(node.expanded);


    useEffect(() => {
        const expandListener = (event: RowEvent) => setExpanded(event.node.expanded);
        node.addEventListener('expandedChanged', expandListener);
        return () => {
            node.removeEventListener('expandedChanged', expandListener);
        }
    }, []);

    const handleOnClick = async () => {
        try {
            const bombLevelData = await getBombLevelData({ 'oid': props.data.oid, 'lid': props.data.lid })
            //console.log('bombleveldata',bombLevelData?.data?.data)
            props.data['children']=bombLevelData?.data?.data
            node.setExpanded(!node.expanded)
        }
        catch (e) {
            console.log(e);
        }
    }

    const onClick = useCallback(() =>
        handleOnClick(),
        [node]
    );

    return (

        <button data-testid='collapsable' style={{ fontSize: "18px", background: "transparent", fontWeight: "bold" }} onClick={onClick}>
            <FlatIcon src={expanded ? "/assets/img/mto/dayWiseCoverage/arrow_down.svg" : "/assets/img/mto/dayWiseCoverage/arrow_right.svg"} />
            {props?.data?.plnt || ''}
        </button>
    )
}

export default customCellRenderer