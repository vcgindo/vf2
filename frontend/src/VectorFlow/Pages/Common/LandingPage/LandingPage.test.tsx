import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import LandingPage from './index'
import { listMenuParent } from '../../../../components/layouts/NavbarMenu/listMenu'

const collectUrls = (item: any): string[] => [
  ...(item.url ? [item.url] : []),
  ...(item.child || []).flatMap(collectUrls)
]

const mockBrowserPermissions = Array.from(
  new Set(
    listMenuParent
      .filter((item: any) => item.app_id !== 1)
      .flatMap(collectUrls)
      .filter(Boolean)
  )
)

jest.mock('../../../../context', () => ({
  useUserData: () => ({
    user: {
      user: { theme_ui: 'NOIRFUSION' },
      roles: {
        permission: ['SuperAdmin', 'Admin', 'VectorConsultant']
      },
      url_permission: mockBrowserPermissions
    }
  })
}))

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (value: string) => value })
}))

describe('VectorFLOW landing application catalog', () => {
  it('renders the seven active MTA/MTO applications shown by the recovered VM reference', async () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    )

    expect(await screen.findAllByText('Click to view')).toHaveLength(7)
    expect(screen.getByText('Planning')).toBeInTheDocument()
    expect(screen.getByText('Guided Insights')).toBeInTheDocument()
    expect(screen.getByText('Research Insights')).toBeInTheDocument()
    expect(screen.getByText('Procurement')).toBeInTheDocument()
    expect(
      screen.getByText('navbar.listMenuParent.prodAndPlanningScheduling.title')
    ).toBeInTheDocument()
    expect(screen.getByText('navbar.listMenuParent.poogi.title')).toBeInTheDocument()
    expect(
      screen.getByText('navbar.listMenuParent.manufacturingHub.title')
    ).toBeInTheDocument()
  })
})
