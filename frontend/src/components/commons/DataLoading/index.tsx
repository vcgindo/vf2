interface DataLoadingProps {
  children: React.ReactNode
  isLoading: boolean
}

const DataLoading = ({ children, isLoading }: DataLoadingProps) => {
  return (
    <>
      {isLoading
        ? (
        <div>
          <>Loading</>
        </div>
          )
        : (
            children
          )}
    </>
  )
}

export default DataLoading
