import { motion } from 'motion/react';
import { Map, History, CreditCard, User } from 'lucide-react';

interface BottomNavProps {
  currentTab: string;
  setTab: (tab: string) => void;
}

export default function BottomNav({ currentTab, setTab }: BottomNavProps) {
  const tabs = [
    { id: 'map', label: 'Mapa', icon: Map },
    { id: 'trips', label: 'Viajes', icon: History },
    { id: 'payments', label: 'Pagos', icon: CreditCard },
    { id: 'profile', label: 'Perfil', icon: User },
  ];

  return (
    <nav className="fixed bottom-0 left-0 w-full z-50 bg-surface/90 backdrop-blur-md flex justify-around items-center px-4 pb-4 pt-3 border-t border-outline-variant/30 ambient-shadow">
      {tabs.map((tab) => {
        const isActive = currentTab === tab.id;
        const Icon = tab.icon;
        
        return (
          <button
            key={tab.id}
            onClick={() => setTab(tab.id)}
            className={`flex flex-col items-center justify-center px-2 py-2 transition-all duration-300 relative group active:scale-95 ${
              isActive ? 'text-primary' : 'text-on-surface-variant/40'
            }`}
          >
            <div className={`p-1.5 rounded-lg transition-colors ${isActive ? 'bg-primary/5' : ''}`}>
              <Icon size={18} className={isActive ? 'stroke-[2.5px]' : 'stroke-[1.5px]'} />
            </div>
            <span className={`ui-label mt-1 text-[7px] ${isActive ? 'opacity-100' : 'opacity-40'}`}>
              {tab.label}
            </span>
            {isActive && (
              <motion.div
                layoutId="activeTabBadge"
                className="absolute top-0 w-8 h-1 bg-primary rounded-b-lg"
                transition={{ type: 'spring', stiffness: 500, damping: 40 }}
              />
            )}
          </button>
        );
      })}
    </nav>
  );
}
