export default function Header() {
  return (
    <header className="w-full border-b border-line bg-paper">
      <div className="h-14 w-full px-4 sm:px-6 flex items-center justify-between gap-4">
        <span className="font-semibold text-ink">Skin Care AI</span>
        <span className="text-meta hidden sm:inline">General skincare guidance, not a diagnosis</span>
      </div>
    </header>
  );
}
