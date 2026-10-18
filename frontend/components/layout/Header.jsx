'use client';

export default function Header() {
  return (
    <header className="fixed top-0 w-full z-50 bg-background border-b border-surface-container-highest">
      <div className="h-12 w-full px-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-label-md tracking-widest uppercase text-on-surface-variant font-medium">
            Skin Care AI
          </span>
          <span className="text-outline-variant font-body-sm select-none">/</span>
          <span className="font-label-sm tracking-wider uppercase text-secondary font-medium">
            Clinical Diagnostic Precision
          </span>
        </div>
        <div className="flex items-center">
          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
            <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
          </div>
        </div>
      </div>
    </header>
  );
}
