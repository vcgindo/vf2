import {
  QueryClient,
  type QueryKey,
  type SetDataOptions
} from '@tanstack/react-query'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      useErrorBoundary: (error: any) => {
        // Request is canceled if token expired (handled in axios-config request interceptor)
        // Don't throw this error to error boundary
        if (error?.message === 'canceled') return false
        return true
      },
      retry: 0
    }
  }
})

export const setupReactQuery = () => {
  return queryClient
}

export const optimisticAddConfig = (queryKey: QueryKey) => {
  return {
    onSuccess: async () => {
      await queryClient.invalidateQueries(queryKey)
    },
    onMutate: async (target: any) => {
      // Cancel any outgoing re-fetches (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries(queryKey)

      const previous = queryClient.getQueryData(queryKey)
      queryClient.setQueryData(queryKey, (old?: any[]) =>
        old != null ? [...old, target] : [target]
      )
      return { previous }
    },
    onError: (_error: any, _data: any, context: any) =>
      queryClient.setQueryData(queryKey, context.previous)
  }
}

export const optimisticUpdateConfig = <T, R>(
  queryKey: QueryKey,
  cacheUpdater?: { updater: (old: T, nw: R) => T, options?: SetDataOptions },
  idKey = 'id'
) => {
  return {
    onSuccess: async () => {
      await queryClient.invalidateQueries(queryKey)
    },
    onMutate: async (target: any) => {
      // Cancel any outgoing re-fetches (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries(queryKey)

      const previous = queryClient.getQueryData<T>(queryKey)

      if (cacheUpdater != null) {
        queryClient.setQueryData(
          queryKey,
          (old: any) => {
            return cacheUpdater.updater(old, target)
          },
          cacheUpdater.options
        )
      } else {
        queryClient.setQueryData(queryKey, (old?: any) => {
          return (
            old?.map((item: any) =>
              item[idKey] === target[idKey] ? { ...item, ...target } : item
            ) != null || []
          )
        })
      }

      return { previous }
    },
    onError: (_error: any, _data: any, context: any) =>
      queryClient.setQueryData(queryKey, context.previous)
  }
}

export const optimisticDeleteConfig = (
  queryKey: QueryKey,
  idKey = 'id'
) => {
  return {
    onSuccess: async () => {
      await queryClient.invalidateQueries(queryKey)
    },
    onMutate: async (target: any) => {
      // Cancel any outgoing re-fetches (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries(queryKey)

      const previous = queryClient.getQueryData(queryKey)
      queryClient.setQueryData(queryKey, (old?: any) => {
        return (
          old?.filter((item: any) => item[idKey] !== target[idKey]) != null || []
        )
      })
      return { previous }
    },
    onError: (_error: any, _data: any, context: any) =>
      queryClient.setQueryData(queryKey, context.previous)
  }
}
