import { AvailabilityComparisonService } from "./api"
import { useMutation } from '@tanstack/react-query'

export const useGetParticularsAvai = () => {
  return useMutation(async (body: any) => {
    return await AvailabilityComparisonService.getTotalParticulars(body)
  })
}