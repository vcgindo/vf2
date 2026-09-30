import { OTIFTags } from "../../../../../../../VectorFlow/Pages/MTO/Common/Enum";
import { Icon } from "./styles";

const TagCellToolTip = (params: any) => {

  if (!(params && params.value && OTIFTags[params.value] && OTIFTags[params.value].split('_'))) {
    return <></>
  }
  const allTags = OTIFTags[params.value].split('_');
  const tags: string[] = [];
  
  if (allTags[1] === 'False') {
    tags.push('ot');
  }
  if (allTags[3] === 'False') {
    tags.push('if');
  }

  if (tags.length === 2) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center' }}>
        <Icon src={`/assets/img/mto/OTIFAnalysis/otif.svg`} />
      </div>

    )
  }

  return (
    <div style={{ height: '100%', display: 'flex', alignItems: 'center' }}>
      {tags.length > 0 && <Icon src={`/assets/img/mto/OTIFAnalysis/${tags[0] === "if" ? "if" : "ot"}.svg`} />}
    </div>
  );
};

export default TagCellToolTip;
