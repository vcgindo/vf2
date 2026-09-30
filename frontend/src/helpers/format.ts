import { DateTime } from 'luxon'

import {format} from 'date-fns'
export const DEFAULT_DATE_FORMAT = 'dd MMM yyyy'
export const DEFAULT_DATE_TIME_FORMAT = 'dd MMM yy, HH:mm'
export const DEFAULT_TIME_FORMAT = 'HH:mm'
export const DD_MMM_YY_FORMAT = 'dd MMM yy'

/**
 * Format user name
 * @returns user full name
 */
export const formatFullName = (
  firstName: string | undefined,
  lastName: string | undefined
) => {
  return ((firstName ? firstName + ' ' : '') + (lastName || '')).trim()
}

/**
 * Format a date or date time, **NOTE** use *formatOptions.timeZone* only for date time
 * @param date UTC date time or date without time component
 * @param formatOptions  format options, timeZone and format
 * @param formatOptions.timeZone Get it from custom hook useUserData().user.timeZone
 * @param formatOptions.format default: dd-MM-yyyy, reference https://moment.github.io/luxon/#/formatting?id=table-of-tokens
 * @returns formatted date
 */
export const formatDate = (
  date: Date | string | number | undefined,
  formatOptions?: { timeZone?: string, format?: string }
) => {
  if (!date) return ''

  const convertOption = formatOptions?.timeZone
    ? { zone: formatOptions.timeZone }
    : undefined
  const format = formatOptions?.format
    ? formatOptions.format
    : DEFAULT_DATE_FORMAT
  return DateTime.fromJSDate(
    typeof date === 'string' || typeof date === 'number'
      ? new Date(date)
      : date,
    convertOption
  ).toFormat(format)
}

/**
 * Format a date or date time, **NOTE** use *formatOptions.timeZone* only for date time
 * @param date UTC date time or date without time component
 * @param timeZone Get it from custom hook useUserData().user.timeZone
 * @param format options, default: dd-MM-yyyy, reference https://moment.github.io/luxon/#/formatting?id=table-of-tokens
 * @returns formatted date
 */
export const formatDateTime = (
  date: Date | string | number | undefined,
  timeZone: string,
  format?: string
) => {
  if (!date) return ''

  const formatType = format || DEFAULT_DATE_TIME_FORMAT
  return DateTime.fromJSDate(
    typeof date === 'string' || typeof date === 'number'
      ? new Date(date)
      : date,
    {
      zone: timeZone
    }
  ).toFormat(formatType)
}

/**
 * Formats a date and time relatively to the current time.
 *
 *  **Sample of using**
 *
 *  const { user } = useUserData();
 *
 *  formatDateTimePretty(date, user.timeZone)
 *
 * **<= 1 min**
 *  - 16:08 (just now)
 * **< 24 hours**
 *  - 16:07 (1 minute ago)
 *  - 22:09 (in 6 hours)
 * **>=24 hours and <= 1 day**
 *  - yesterday
 *  - tomorrow
 * **<= 30 days**
 *  - 30 Jul (3 weeks ago)
 *  - 8 Aug (9 days ago)
 *  - 27 Aug (in 10 days)
 *  - 16 Sep (in 4 weeks)
 * **> 30 days**
 *  - 30 Apr 2022
 *  - 20 Oct 2022
 * **Different year**
 *  - 12 Apr 2021
 *  - 12 Apr 2023
 * @param date UTC date time received from backend service
 * @param timeZone Get it from custom hook useUserData().user.timeZone
 */
export const formatDateTimePretty = (date: Date, timeZone: string) => {
  if (!date) return ''

  const now = DateTime.now()
  const dt = DateTime.fromJSDate(
    typeof date === 'string' ? new Date(date) : date,
    { zone: timeZone }
  )
  const isPast = dt < now

  // remove second component before compare
  const diffHour = Math.trunc(
    Math.abs(dt.startOf('minute').diff(now.startOf('minute'), 'hours').hours)
  )
  // remove time components before compare
  const diffDays = Math.abs(
    dt.startOf('day').diff(now.startOf('day'), 'days').days
  )
  const diffYears = dt.year - now.year

  let formatted = ''
  const IN = isPast ? '' : 'in '
  const AGO = isPast ? ' ago' : ''

  /* within 24 hours */
  if (diffHour < 24) {
    formatted = dt.toFormat('HH:mm')
    const diffMin = Math.trunc(Math.abs(dt.diff(now, 'minutes').minutes))

    if (diffMin < 1) {
      if (isPast) {
        // past within 1 min
        return `${formatted} (just now)`
      } else {
        // future within 1 min
        return formatted
      }
    } else {
      if (diffHour >= 1) {
        // more than 1 hour
        return `${formatted} (${IN}${diffHour} hour${
          diffHour > 1 ? 's' : ''
        }${AGO})`
      } else {
        // more than 1 min
        return `${formatted} (${IN}${diffMin} minute${
          diffMin > 1 ? 's' : ''
        }${AGO})`
      }
    }
  } else if (diffYears === 0) {
    /* this year */
    formatted = dt.toFormat(DEFAULT_DATE_FORMAT)
    // within 30 days
    if (diffDays <= 30) {
      formatted = dt.toFormat('dd MMM')
      // remove time components before compare
      const diffWeeks = Math.trunc(
        Math.abs(dt.startOf('day').diff(now.startOf('day'), 'weeks').weeks)
      )

      // more than 15 days
      if (diffDays >= 15) {
        return `${formatted} (${IN}${diffWeeks} weeks${AGO})`
      } else if (diffDays > 1) {
        return `${formatted} (${IN}${diffDays} days${AGO})`
      } else {
        return `${formatted} (${isPast ? 'yesterday' : 'tomorrow'})`
      }
    } else {
      return formatted
    }
  } else {
    return dt.toFormat(DEFAULT_DATE_FORMAT)
  }
}

/**
 * Format phone number for displaying and submitting
 * @param telcoCode phone prefix (eg, +65)
 * @param phoneNumber
 * @param forSubmitting
 * @returns if for submitting +6587654321 else (+65) 87654321
 */

export const formatPhoneNumber = (
  telcoCode?: string,
  phoneNumber?: string,
  forSubmitting?: boolean
) => {
  if (!phoneNumber) {
    return ''
  }
  if (!telcoCode) {
    return phoneNumber
  }
  const number = parseInt(phoneNumber, 10)
  if (forSubmitting) {
    return `${telcoCode}${number}`
  }
  return `(${telcoCode}) ${number}`
}


export function formatMDMDate(inputDate:string, dateFormat?:string) {
  try{
    const parsedDate = new Date(inputDate)

  const myFormat = dateFormat ?dateFormat: 'dd/MMM/yy hh:mm:ss a'

  const formattedDate = format(parsedDate,myFormat)

  return formattedDate;
  }catch(err){
    console.log(err)
  }
}