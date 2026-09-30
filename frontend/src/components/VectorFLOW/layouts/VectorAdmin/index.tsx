import {ReactNode} from 'react'

import {AdminLayoutContent, AdminLayoutWrapper} from './styles'

interface VectorAdminLayoutProps{
    children:ReactNode
}

const VectorAdminLayout = (props:VectorAdminLayoutProps)=>{

    const {
        children
    } = props

    return(
        <AdminLayoutWrapper>
            <AdminLayoutContent>
            {children}
            </AdminLayoutContent>
        </AdminLayoutWrapper>
    )
}

export default VectorAdminLayout