/**
 * Small inline icons needed only by the Product Listing page's luxe redesign
 * (wishlist heart, filter sliders, bottom-nav home) -- kept local to this
 * route rather than added to the shared Home icon set, since nothing else
 * uses them.
 */

type IconProps = { size?: number; className?: string };

/*
 * A properly symmetric heart -- mirror-imaged left/right around x=12, so it
 * sits dead-center in its viewBox at any size (the previous path was
 * lopsided: its two lobes had different curves, so it always looked
 * off-center inside the wishlist button no matter how the button itself
 * was aligned).
 */
const HEART_PATH =
  'M12 20.5c-.24 0-.47-.08-.66-.23C6.6 16.87 3.5 14 3.5 10.5 3.5 7.8 5.6 5.75 8.25 5.75c1.53 0 2.97.73 3.75 1.9.78-1.17 2.22-1.9 3.75-1.9 2.65 0 4.75 2.05 4.75 4.75 0 3.5-3.1 6.37-7.84 9.77-.19.15-.42.23-.66.23Z';

export const HeartIcon = ({
  size = 16,
  filled = false,
  className,
}: IconProps & { filled?: boolean }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    className={className}
    fill={filled ? 'currentColor' : 'none'}
    stroke="currentColor"
    strokeWidth={filled ? 0 : 1.6}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d={HEART_PATH} />
  </svg>
);

export const SlidersIcon = ({ size = 15, className }: IconProps) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.6}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M4 7h8M16 7h4" />
    <circle cx="13" cy="7" r="2.2" />
    <path d="M4 12h2M10 12h10" />
    <circle cx="7" cy="12" r="2.2" />
    <path d="M4 17h10M18 17h2" />
    <circle cx="16" cy="17" r="2.2" />
  </svg>
);

export const HomeIcon = ({ size = 20, className }: IconProps) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.6}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M4 11.5 12 4l8 7.5" />
    <path d="M6 10v9h12v-9" />
  </svg>
);
