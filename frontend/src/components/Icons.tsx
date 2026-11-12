import type { ReactNode, SVGProps } from 'react'

interface IconProps extends SVGProps<SVGSVGElement> {
  size?: number | string
  'aria-label'?: string
}

/** Ícones de traço 1.75px, 24×24. Decorativos por padrão (aria-hidden). */
const createIcon = (paths: ReactNode) => {
  const Icon = (props: IconProps) => {
    const { size = 20, 'aria-label': ariaLabel, className, style, ...rest } = props
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        role={ariaLabel ? 'img' : undefined}
        aria-label={ariaLabel}
        aria-hidden={ariaLabel ? undefined : true}
        focusable="false"
        className={className}
        style={{ width: size, height: size, ...style }}
        {...rest}
      >
        {paths}
      </svg>
    )
  }
  return Icon
}

/* Barbearia */
export const ScissorsIcon = createIcon(<><circle cx="6" cy="6" r="3" /><circle cx="6" cy="18" r="3" /><path d="M8.12 8.12 12 12" /><path d="M20 4 8.12 15.88" /><path d="M14.8 14.8 20 20" /></>)
export const RazorIcon = createIcon(<><path d="M4 15 15 4l3 3L7 18z" /><path d="m7 18-3 3" /><path d="M15 4l2-2" /></>)
export const ChairIcon = createIcon(<><path d="M7 11V5a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v6" /><path d="M5 11h14v4H5z" /><path d="M8 15v5M16 15v5M6 20h12" /></>)
export const StoreIcon = createIcon(<><path d="M3 9 4.5 4h15L21 9" /><path d="M3 9h18v1.5a3 3 0 0 1-6 0 3 3 0 0 1-6 0 3 3 0 0 1-6 0z" /><path d="M5 12.5V20h14v-7.5" /><path d="M10 20v-4h4v4" /></>)

/* Agenda e tempo */
export const ClockIcon = createIcon(<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>)
export const CalendarIcon = createIcon(<><rect x="3" y="4.5" width="18" height="16.5" rx="2" /><path d="M16 2.5v4M8 2.5v4M3 10h18" /></>)
export const CalendarPlusIcon = createIcon(<><rect x="3" y="4.5" width="18" height="16.5" rx="2" /><path d="M16 2.5v4M8 2.5v4M3 10h18M12 13.5v5M9.5 16h5" /></>)
export const CalendarCheckIcon = createIcon(<><rect x="3" y="4.5" width="18" height="16.5" rx="2" /><path d="M16 2.5v4M8 2.5v4M3 10h18" /><path d="m9 15.5 2 2 4-4" /></>)
export const HistoryIcon = createIcon(<><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5" /><path d="M12 7v5l3 2" /></>)

/* Pessoas */
export const UserIcon = createIcon(<><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>)
export const UsersIcon = createIcon(<><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0" /><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8" /><path d="M18 14.2a6.5 6.5 0 0 1 3.5 5.8" /></>)
export const UserPlusIcon = createIcon(<><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0" /><path d="M19 8v6M16 11h6" /></>)
export const ContactIcon = createIcon(<><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="9.5" cy="10.5" r="2.5" /><path d="M5.5 17a4 4 0 0 1 8 0" /><path d="M15.5 9.5h3M15.5 13h3" /></>)

/* Navegação */
export const HomeIcon = createIcon(<><path d="M3 10.5 12 3l9 7.5" /><path d="M5 9v12h14V9" /><path d="M10 21v-6h4v6" /></>)
export const DashboardIcon = createIcon(<><rect x="3" y="3" width="7.5" height="9" rx="1.5" /><rect x="13.5" y="3" width="7.5" height="5" rx="1.5" /><rect x="13.5" y="11" width="7.5" height="10" rx="1.5" /><rect x="3" y="15" width="7.5" height="6" rx="1.5" /></>)
export const MenuIcon = createIcon(<path d="M4 6h16M4 12h16M4 18h16" />)
export const ChevronLeftIcon = createIcon(<path d="m15 18-6-6 6-6" />)
export const ChevronRightIcon = createIcon(<path d="m9 18 6-6-6-6" />)
export const ChevronDownIcon = createIcon(<path d="m6 9 6 6 6-6" />)
export const ChevronUpIcon = createIcon(<path d="m18 15-6-6-6 6" />)
export const ArrowLeftIcon = createIcon(<path d="M19 12H5M11 18l-6-6 6-6" />)
export const PanelLeftIcon = createIcon(<><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M9 3v18" /></>)
export const SortIcon = createIcon(<path d="m7 15 5 5 5-5M7 9l5-5 5 5" />)

/* Ações */
export const XIcon = createIcon(<path d="M18 6 6 18M6 6l12 12" />)
export const PlusIcon = createIcon(<path d="M12 5v14M5 12h14" />)
export const MinusIcon = createIcon(<path d="M5 12h14" />)
export const CheckIcon = createIcon(<path d="M20 6 9 17l-5-5" />)
export const SearchIcon = createIcon(<><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></>)
export const FilterIcon = createIcon(<path d="M3 5h18l-7 8.5V20l-4-2v-4.5z" />)
export const EditIcon = createIcon(<><path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z" /></>)
export const TrashIcon = createIcon(<><path d="M3 6h18" /><path d="M8 6V4h8v2" /><path d="M19 6l-1 14H6L5 6" /></>)
export const PowerIcon = createIcon(<><path d="M12 2v10" /><path d="M18.4 6.6a9 9 0 1 1-12.8 0" /></>)
export const RotateCcwIcon = createIcon(<><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5" /></>)
export const RefreshIcon = createIcon(<><path d="M21 12a9 9 0 0 1-15 6.7L3 16" /><path d="M3 12a9 9 0 0 1 15-6.7L21 8" /><path d="M3 21v-5h5M21 3v5h-5" /></>)
export const LogoutIcon = createIcon(<><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="m16 17 5-5-5-5" /><path d="M21 12H9" /></>)
export const SettingsIcon = createIcon(<><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></>)
export const KeyIcon = createIcon(<><circle cx="7.5" cy="15.5" r="4.5" /><path d="m10.7 12.3 9.8-9.8M17 6l3 3M15 8l2 2" /></>)
export const EyeIcon = createIcon(<><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" /></>)
export const EyeOffIcon = createIcon(<><path d="M10.6 5.1A9.9 9.9 0 0 1 12 5c6.5 0 10 7 10 7a17.6 17.6 0 0 1-2.4 3.4" /><path d="M6.6 6.6C3.7 8.4 2 12 2 12s3.5 7 10 7a9.7 9.7 0 0 0 5.4-1.6" /><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" /><path d="m2 2 20 20" /></>)
export const MailIcon = createIcon(<><rect x="2.5" y="4.5" width="19" height="15" rx="2" /><path d="m3 6 9 7 9-7" /></>)
export const PhoneIcon = createIcon(<path d="M21 16.5v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 1.1 3.7 2 2 0 0 1 3.1 1.5h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L7.1 9.2a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.8 2z" />)
export const LocationIcon = createIcon(<><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0z" /><circle cx="12" cy="10" r="3" /></>)
export const LockIcon = createIcon(<><rect x="4" y="11" width="16" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></>)
export const BellIcon = createIcon(<><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" /></>)

/* Estados */
export const CheckCircleIcon = createIcon(<><circle cx="12" cy="12" r="9" /><path d="m8.5 12 2.5 2.5 4.5-5" /></>)
export const XCircleIcon = createIcon(<><circle cx="12" cy="12" r="9" /><path d="m15 9-6 6M9 9l6 6" /></>)
export const AlertCircleIcon = createIcon(<><circle cx="12" cy="12" r="9" /><path d="M12 8v4.5M12 16h.01" /></>)
export const AlertTriangleIcon = createIcon(<><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /><path d="M12 9v4M12 17h.01" /></>)
export const InfoIcon = createIcon(<><circle cx="12" cy="12" r="9" /><path d="M12 16v-4.5M12 8h.01" /></>)
export const WifiOffIcon = createIcon(<><path d="m2 2 20 20" /><path d="M8.5 16.5a5 5 0 0 1 7 0M5 13a10 10 0 0 1 5.2-2.8M19 13a10 10 0 0 0-2.3-1.7M2 8.8a15 15 0 0 1 4.2-2.7M22 8.8A15 15 0 0 0 10.7 5" /><path d="M12 20h.01" /></>)

/* Indicadores */
export const TrendingUpIcon = createIcon(<><path d="m22 7-8.5 8.5-5-5L2 17" /><path d="M16 7h6v6" /></>)
export const ReceiptIcon = createIcon(<><path d="M5 2v20l2.5-1.5L10 22l2-1.5 2 1.5 2.5-1.5L19 22V2l-2.5 1.5L14 2l-2 1.5L10 2 7.5 3.5z" /><path d="M9 8h6M9 12h6M9 16h3" /></>)
export const AnalyticsIcon = createIcon(<path d="M18 20V10M12 20V4M6 20v-6" />)

/* Nomes legados mantidos por compatibilidade */
export const StarIcon = createIcon(<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z" />)
export const BadgeIcon = ContactIcon
export const BuildingIcon = StoreIcon
