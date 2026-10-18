import './globals.css';
import Header from '../components/layout/Header';
import Footer from '../components/layout/Footer';

export const metadata = {
  title: 'Skin Care AI — Clinical Diagnostic Precision',
  description: 'AI-powered skin care analysis and clinical diagnostic consultation.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
          rel="stylesheet"
        />
      </head>
      <body className="bg-background font-body-md text-on-surface min-h-screen flex flex-col antialiased">
        <Header />
        <main className="w-full pt-12 flex-1 flex flex-col bg-background">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
