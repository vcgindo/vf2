interface ErrorsProps {
  errors: any
  name: string
  style?: any
}
const Errors = ({ style, errors, name }: ErrorsProps) => {
  const renderError = () => {
    const text = name.replace(/_/g, " ")
    switch (errors[name].type) {
      case 'required':
        return `This ${text} is required field`
      case 'minLength':
        return `${errors[name].message}`

      case 'maxLength':
        return `${errors[name].message}`

      case 'pattern':
        return `${errors[name].message}`
      case 'validate':
        return `${errors[name].message}`
      default:
        return null
    }
  }
  return (
    <p style={{ color: 'red', marginTop: 10, fontSize: 12,maxWidth:'350px',...style}}>
      {errors[name] && renderError()}
    </p>
  )
}

export default Errors
