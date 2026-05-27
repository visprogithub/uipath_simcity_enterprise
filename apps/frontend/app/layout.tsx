import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Maestro City — Healthcare Enterprise Operations Simulation',
  description:
    'Real-time healthcare enterprise operations simulation with AI agents, UiPath automation, and crisis management.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} dark`}>
      <body className="bg-bg-base text-text-primary antialiased font-sans h-screen overflow-hidden">
        {children}
      </body>
    </html>
  );
}
