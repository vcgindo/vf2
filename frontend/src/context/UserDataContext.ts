import React, {  useContext } from 'react'

export interface Permission {
  canView: boolean
  canCreate: boolean
  canModify: boolean
  canDelete: boolean
  featurePermission: {
    viewAll: boolean
    create: boolean
    modifyAll: boolean
    deleteAll: boolean
  }
}

export interface UserData {
  user: any,
  setUser?: any,
  changeColorTheme: (color: string) => void,
  isSideBarOpen:boolean,
  toggleSideBar:any
}

export const UserDataContext = React.createContext<UserData>({
  user: {
    id: 0,
    email: '',
    name: '',
    is_admin: false,
    role: ''
    
  },
  setUser: null,
  changeColorTheme: (color) => {return color},
  isSideBarOpen:false,
  toggleSideBar:()=>{return}
})

UserDataContext.displayName = 'UserDataContext'

export const useUserData = () => useContext(UserDataContext)
