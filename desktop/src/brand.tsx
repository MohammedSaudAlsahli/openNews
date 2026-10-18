// Same geometry as brand/mark.svg; currentColor adapts to both app themes.
export function BrandMark({ className = "" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 100 100"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M59 23H42C31.5 23 23 31.5 23 42V58C23 68.5 31.5 77 42 77H58C68.5 77 77 68.5 77 58V41"
        stroke="currentColor"
        strokeWidth="12"
        strokeLinecap="round"
      />
    </svg>
  );
}
