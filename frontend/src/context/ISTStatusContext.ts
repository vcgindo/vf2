/* eslint-disable @typescript-eslint/no-empty-function */
import { createContext } from 'react'

interface ISTStatusContextType {
  currentAction: string
  setCurrentAction: (action: string) => void
  exportView: boolean
  setExportView: (status: boolean) => void
  currentViewName: string
  setCurrentViewName: (viewName: string) => void
  currentViewCount: number
  setCurrentViewCount: (viewCount: number) => void
  currentDataCount: number
  setCurrentDataCount: (dataCount: number) => void
}

export const ISTStatusContext = createContext<ISTStatusContextType>({
  currentAction: 'edit',
  setCurrentAction: () => { },
  exportView: false,
  setExportView: () => { },
  currentViewName: 'Create Your Own Report',
  setCurrentViewName: () => { },
  currentViewCount: 0,
  setCurrentViewCount: () => { },
  currentDataCount: 0,
  setCurrentDataCount: () => { }
})
