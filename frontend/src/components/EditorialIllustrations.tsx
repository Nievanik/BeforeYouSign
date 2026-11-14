import React from 'react'

/**
 * Editorial, playful vector illustrations inspired by boutique creative studio branding.
 * Palette:
 * - Burnt Orange: #DA4324
 * - Deep Olive Green: #3E4928 / #43512D
 * - Soft Apricot: #E9AD70
 * - Warm Beige: #D8C9B3
 * - Warm Ivory: #FAF3E9
 */

export const StorefrontIllustration: React.FC<{ className?: string; size?: number }> = ({
  className = '',
  size = 72,
}) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 100 100"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={`editorial-illus ${className}`}
    aria-hidden="true"
  >
    {/* Ground line */}
    <path d="M8 88H92" stroke="#3E4928" strokeWidth="3" strokeLinecap="round" />
    
    {/* Main Storefront Body */}
    <rect x="20" y="38" width="60" height="50" rx="3" fill="#FAF3E9" stroke="#3E4928" strokeWidth="3" />
    
    {/* Door */}
    <rect x="54" y="52" width="18" height="36" rx="2" fill="#E9AD70" stroke="#3E4928" strokeWidth="2.5" />
    <circle cx="58" cy="70" r="1.5" fill="#3E4928" />
    
    {/* Display Window */}
    <rect x="27" y="52" width="21" height="24" rx="2" fill="#FAF3E9" stroke="#3E4928" strokeWidth="2.5" />
    <line x1="37.5" y1="52" x2="37.5" y2="76" stroke="#D8C9B3" strokeWidth="1.5" />
    <line x1="27" y1="64" x2="48" y2="64" stroke="#D8C9B3" strokeWidth="1.5" />
    {/* Little plant pot in window */}
    <path d="M34 72H41L40 76H35L34 72Z" fill="#DA4324" />
    <circle cx="37.5" cy="70" r="2.5" fill="#3E4928" />

    {/* Striped Awning */}
    <path
      d="M16 38C16 38 18 22 50 22C82 22 84 38 84 38H16Z"
      fill="#FAF3E9"
      stroke="#3E4928"
      strokeWidth="3"
    />
    {/* Scalloped Awning Stripes */}
    <path d="M16 38C19 43 25 43 28 38C31 43 37 43 40 38C43 43 49 43 52 38C55 43 61 43 64 38C67 43 73 43 76 38C79 43 83 41 84 38" stroke="#3E4928" strokeWidth="2.5" fill="none" />
    {/* Orange Awning Panels */}
    <path d="M28 24L28 38C31 43 37 43 40 38L40 22.5" fill="#DA4324" stroke="#3E4928" strokeWidth="2" />
    <path d="M52 22.5L52 38C55 43 61 43 64 38L64 24" fill="#DA4324" stroke="#3E4928" strokeWidth="2" />
    
    {/* Little Chimney / Vent */}
    <rect x="26" y="16" width="6" height="8" rx="1" fill="#E9AD70" stroke="#3E4928" strokeWidth="2" />
    {/* Tiny Smoke / Idea Puff */}
    <path d="M29 12C28 10 32 8 30 6" stroke="#DA4324" strokeWidth="2" strokeLinecap="round" />

    {/* Playful Floating Star / Sparkle */}
    <path
      d="M84 14C84 18 88 18 88 18C88 18 84 18 84 22C84 18 80 18 80 18C80 18 84 18 84 14Z"
      fill="#DA4324"
    />
  </svg>
)

export const SparkleDoodle: React.FC<{ size?: number; color?: string; className?: string }> = ({
  size = 18,
  color = '#DA4324',
  className = '',
}) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={`sparkle-doodle ${className}`}
    aria-hidden="true"
  >
    <path
      d="M12 2C12 7.5 16.5 12 22 12C16.5 12 12 16.5 12 22C12 16.5 7.5 12 2 12C7.5 12 12 7.5 12 2Z"
      fill={color}
    />
  </svg>
)

export const PinDoodle: React.FC<{ size?: number; className?: string }> = ({
  size = 24,
  className = '',
}) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    aria-hidden="true"
  >
    <path
      d="M12 2C8.13401 2 5 5.13401 5 9C5 14.25 12 22 12 22C12 22 19 14.25 19 9C19 5.13401 15.866 2 12 2Z"
      fill="#43512D"
      stroke="#FAF3E9"
      strokeWidth="2"
    />
    <circle cx="12" cy="9" r="3" fill="#FAF3E9" />
  </svg>
)

export const CoffeeShopDoodle: React.FC<{ size?: number; className?: string }> = ({
  size = 28,
  className = '',
}) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    aria-hidden="true"
  >
    {/* Mug Body */}
    <path
      d="M6 10H22V20C22 23.3137 19.3137 26 16 26H12C8.68629 26 6 23.3137 6 20V10Z"
      fill="#FAF3E9"
      stroke="#3E4928"
      strokeWidth="2.5"
    />
    {/* Handle */}
    <path
      d="M22 12H24C25.6569 12 27 13.3431 27 15V17C27 18.6569 25.6569 20 24 20H22"
      stroke="#3E4928"
      strokeWidth="2.5"
      strokeLinecap="round"
    />
    {/* Steam */}
    <path
      d="M10 5C10 5 11 6.5 10 7.5"
      stroke="#DA4324"
      strokeWidth="2"
      strokeLinecap="round"
    />
    <path
      d="M14 4C14 4 15 5.5 14 6.5"
      stroke="#DA4324"
      strokeWidth="2"
      strokeLinecap="round"
    />
    <path
      d="M18 5C18 5 19 6.5 18 7.5"
      stroke="#DA4324"
      strokeWidth="2"
      strokeLinecap="round"
    />
  </svg>
)

export const NeighborhoodTreeDoodle: React.FC<{ size?: number; className?: string }> = ({
  size = 24,
  className = '',
}) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    aria-hidden="true"
  >
    {/* Trunk */}
    <line x1="12" y1="14" x2="12" y2="22" stroke="#3E4928" strokeWidth="2.5" strokeLinecap="round" />
    {/* Leaves */}
    <circle cx="12" cy="9" r="7" fill="#43512D" stroke="#3E4928" strokeWidth="2" />
    <circle cx="10" cy="7.5" r="2" fill="#E9AD70" />
  </svg>
)
