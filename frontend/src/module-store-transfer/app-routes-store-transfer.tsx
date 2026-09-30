import React from 'react'
import { type RouteObject } from 'react-router'
import { LazyLoad } from '../components'

const ManualUpload = React.lazy(
  async () => await import('./pages/manual-upload/index')
)

export const getStoreTransferModuleRoutes = (): RouteObject[] => {
  return [
    {
      children: [
        {
          index: true,
          element: LazyLoad(<ManualUpload />)
        }
      ]
    }
  ]
}
