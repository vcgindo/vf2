import React from 'react'
import { type RouteObject } from 'react-router'
import { LazyLoad } from '../components'

const Profile = React.lazy(async () => await import('./pages/profile'))

export const getMainModuleRoutes = (): RouteObject[] => {
  return [
    {
      children: [
        {
          index: true,
          element: LazyLoad(<Profile />)
        }
      ]
    }
  ]
}
