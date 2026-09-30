import {useState} from 'react'

import {RemarkModalTableCell, RemarkModalUserIcon, UserToolTip,UserToolTipContent } from "./styles"


const UserIcon = ({data}:{data:string})=>{

    const [isToolTipOpen,toggleToolTip] = useState<boolean>(false)

    return(
        <RemarkModalTableCell>
            <RemarkModalUserIcon onMouseEnter={()=>toggleToolTip(true)} onMouseLeave={()=>toggleToolTip(false)}>
                {data.slice(0,1)}
            </RemarkModalUserIcon>
            {(isToolTipOpen) && (
                <UserToolTip >
                    <UserToolTipContent>{data}</UserToolTipContent>
                </UserToolTip>
            )}
        </RemarkModalTableCell>
    )
}

export default UserIcon