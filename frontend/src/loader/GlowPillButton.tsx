import React from "react";

interface GlowPillButtonProps {
  label: string;
  disabled?: boolean;
  onClick?: () => void;
}

const ArrowIcon: React.FC = () => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 14 14"
    fill="none"
    aria-hidden="true"
  >
    <path
      d="M2.5 7h9M7.5 3l4 4-4 4"
      stroke="rgba(255,255,255,0.75)"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const GlowPillButton: React.FC<GlowPillButtonProps> = ({
  label,
  disabled = false,
  onClick,
}) => {
  return (
    <button
      className="glow-pill"
      disabled={disabled}
      onClick={disabled ? undefined : onClick}
      type="button"
    >
      <span className="glow-pill__disc">
        {/* Glow ring sits behind the arrow via absolute positioning */}
        <span className="glow-ring" aria-hidden="true" />
        <span className="glow-pill__arrow">
          <ArrowIcon />
        </span>
      </span>
      <span className="glow-pill__label">{label}</span>
    </button>
  );
};

export default GlowPillButton;
