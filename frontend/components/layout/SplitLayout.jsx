export default function SplitLayout({ leftPanel, rightPanel }) {
  return (
    <div className="w-full flex-1 grid grid-cols-1 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <section className="px-4 py-8 sm:px-8 sm:py-10 lg:px-12 lg:py-12 border-b lg:border-b-0 lg:border-r border-line bg-panel">
        {leftPanel}
      </section>
      <section className="px-4 py-8 sm:px-8 sm:py-10 lg:px-12 lg:py-12 bg-paper min-w-0">
        {rightPanel}
      </section>
    </div>
  );
}
