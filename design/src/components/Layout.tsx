import { motion } from 'motion/react';
import type { ReactNode } from 'react';

interface LayoutProps {
  children: ReactNode;
  showNav?: boolean;
  currentTab?: string;
  setTab?: (tab: string) => void;
  headerTitle?: string;
  onBack?: () => void;
  headerRight?: ReactNode;
}

export default function Layout({ 
  children, 
  showNav = true, 
  currentTab = 'map', 
  setTab = () => {},
  headerTitle,
  onBack,
  headerRight
}: LayoutProps) {
  return (
    <div className="min-h-screen flex flex-col max-w-lg mx-auto bg-surface relative overflow-x-hidden">
      {(headerTitle || headerRight) && (
        <header className="fixed top-0 w-full max-w-lg z-50 flex items-center justify-between px-6 h-20 glass-nav">
          <div className="flex items-center gap-4">
            {onBack && (
              <button onClick={onBack} className="text-secondary active:scale-90 transition-transform hover:text-primary">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
              </button>
            )}
            <h1 className="font-headline font-extrabold text-lg tracking-tight text-primary">
              {headerTitle}
            </h1>
          </div>
          {headerRight || (
            <div className="text-2xl font-headline font-black tracking-tighter text-primary">GIRO</div>
          )}
        </header>
      )}
      
      <main className={`flex-grow ${headerTitle ? 'pt-24' : ''} ${showNav ? 'pb-32' : ''}`}>
        {children}
      </main>

      {showNav && (
        <div className="max-w-lg w-full">
          {/* Using the component logic elsewhere but defining the shell here if needed or just importing it */}
        </div>
      )}
    </div>
  );
}
