import {ITooltipParams} from 'ag-grid-enterprise'

import {CategoryToolTipWrapper,CategoryToolTipSection,CategoryToolTipSectionHeader,CategoryToolTipSectionDescription} from './styles'
import { BTRCategoryMapper } from "../../../../../helpers/BPRConstants"

const CategoryToolTip = (params:ITooltipParams)=>{
    const categories = params.value.split("|")
    
    return(
        <CategoryToolTipWrapper>
            {categories.map((c:string)=>{
                const categoryData = BTRCategoryMapper[c]
                if(categoryData){
                    if(c==='BR'){
                        return (
                            <CategoryToolTipSection style={{background:'black',color:'white'}}>
                                <CategoryToolTipSectionHeader>
                                    {categoryData.toolTipHeader}
                                </CategoryToolTipSectionHeader>
                                <CategoryToolTipSectionDescription>
                                    {categoryData.toolTipDescription}
                                </CategoryToolTipSectionDescription>
                            </CategoryToolTipSection>
                        )
                    }
                    return(
                        <CategoryToolTipSection style={{backgroundColor:categoryData.bgColor,color:categoryData.color}}>
                            <CategoryToolTipSectionHeader>
                                {categoryData.toolTipHeader}
                            </CategoryToolTipSectionHeader>
                            <CategoryToolTipSectionDescription>
                                {categoryData.toolTipDescription}
                            </CategoryToolTipSectionDescription>
                        </CategoryToolTipSection>
                    )
                }
            })}        
        </CategoryToolTipWrapper>
    )
}

export default CategoryToolTip