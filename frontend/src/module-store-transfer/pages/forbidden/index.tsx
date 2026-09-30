import { SCPageForbidden, PermissionForbiddenIcon } from './styles'

const PageForbidden = () => {
  const params = new URLSearchParams(window.location.search);
  const URLPermission = params.get("URLPermission");
  return (
    <SCPageForbidden>
      {URLPermission ?
        <PermissionForbiddenIcon
          src="/assets/img/error-403.svg"
        /> :
        <PermissionForbiddenIcon
          src="/assets/img/error-403-page.svg"
        />
      }
    </SCPageForbidden>
  )
}

export default PageForbidden
