'use client';

export default function Button({ children, type = 'button', disabled = false, onClick, className = '' }) {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`w-full sm:w-auto px-8 py-3 bg-primary-container text-on-primary font-label-md uppercase tracking-wider rounded hover:bg-primary transition-colors duration-150 text-center select-none disabled:opacity-60 disabled:cursor-not-allowed ${className}`}
    >
      {children}
    </button>
  );
}
