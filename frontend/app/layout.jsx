import { IBM_Plex_Sans, Source_Serif_4 } from 'next/font/google';
import './globals.css';
import Header from '../components/layout/Header';
import Footer from '../components/layout/Footer';

const plex = IBM_Plex_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-plex',
  display: 'swap',
});

const sourceSerif = Source_Serif_4({
  subsets: ['latin'],
  weight: ['600', '700'],
  variable: '--font-source-serif',
  display: 'swap',
});

export const metadata = {
  title: 'Skin Care AI',
  description:
    'Describe a skin concern by typing or speaking and get cautious, general skincare guidance. Not a medical diagnosis.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${plex.variable} ${sourceSerif.variable}`}>
      <body className="min-h-screen flex flex-col antialiased">
        <Header />
        <main className="w-full flex-1 flex flex-col">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
