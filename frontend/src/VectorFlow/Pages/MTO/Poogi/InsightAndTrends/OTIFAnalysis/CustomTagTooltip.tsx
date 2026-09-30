import { CustomTooltipProps } from '@ag-grid-community/react';
import { OTIFTags } from '../../../Common/Enum';
import { Tag, TextWrapper } from './TagCellRenderer/styles';

export default (props: CustomTooltipProps & { color: string }) => {

    console.log(props.value, 'CUSTOM');
    const allTags = OTIFTags[props.value].split('_');
    const tags: string[] = [];
    console.log(allTags);
    if(allTags[1] === 'False'){
        tags.push('ot');
    }
    if(allTags[3] === 'False'){
        tags.push('if');
    }

    console.log(tags, 'ENUM')

    return (
        <div className="custom-tooltip">
            {tags.length > 0 && <TextWrapper>
                {tags?.map((s, index) => {
                    return (
                        <Tag
                        style={{
                            background: `${s === "if" ? "#FEA236" : "#D1750C"}`,
                        }}
                        key={`${index + s}`}
                        >
                        {s === "if" ? "IF Failed" : "OT Failed"}
                        </Tag>
                    );
                })}
            </TextWrapper>}
        </div>
    );
};
