import { Outlet } from 'react-router'

const ModuleLayout = () => {
  return (
    <div id="module-layout">
      <main>
        <Outlet />
      </main>
    </div>
  )
}

export default ModuleLayout
