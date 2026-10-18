'use client';

export default function SplitLayout({ leftPanel, rightPanel }) {
  return (
    <div className="w-full min-h-[calc(100vh-4rem)] flex flex-col lg:flex-row bg-background">
      {/* LEFT PANEL: 40% Width on Desktop */}
      <section className="w-full lg:w-[40%] flex flex-col justify-between p-8 sm:p-10 lg:p-12 border-b lg:border-b-0 lg:border-r border-surface-container-highest bg-surface-container-low shrink-0">
        {leftPanel}
      </section>

      {/* RIGHT PANEL: 60% Width on Desktop */}
      <section className="w-full lg:w-[60%] flex flex-col h-full bg-background overflow-y-auto">
        {rightPanel}
      </section>
    </div>
  );
}
