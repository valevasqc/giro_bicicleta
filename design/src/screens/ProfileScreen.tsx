import { motion } from 'motion/react';
import { Bolt, Route, Leaf, ChevronRight, History, CreditCard, HelpCircle, Plus } from 'lucide-react';

interface ProfileScreenProps {
  onLogout: () => void;
  onNavigateHistory: () => void;
  onNavigatePayments: () => void;
  onNavigateSupport: () => void;
}

export default function ProfileScreen({ onLogout, onNavigateHistory, onNavigatePayments, onNavigateSupport }: ProfileScreenProps) {
  const menuItems = [
    { label: 'Historial de viajes', icon: History, action: onNavigateHistory },
    { label: 'Métodos de pago', icon: CreditCard, action: onNavigatePayments },
    { label: 'Ayuda y Soporte', icon: HelpCircle, action: onNavigateSupport },
  ];

  return (    <div className="min-h-screen bg-surface flex flex-col">
      <header className="fixed top-0 w-full max-w-lg z-50 flex justify-between items-center px-6 h-20 bg-surface/80 backdrop-blur-md">
        <div className="text-2xl font-headline font-black tracking-tighter text-primary">GIRO</div>
        <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-primary/20 p-0.5">
          <img 
            alt="User Profile" 
            className="w-full h-full object-cover rounded-full grayscale" 
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuANsAxqnX-lZLHDkC9ZrPx3XDLnFGNYrIKXHlcgk7StMFpHJsnP2pJ58eR7umIWCkePjfj4F6fCDuWdUWTa1qcXBCoAYKX_6z4Cz6J5UgYPLO6B3FRbkj9EUg5tQQUibv2IrmszyB7vnFGAEcD-Xhvua-cOexx-1f_Iu9ne7AmOqw0dw-1oeobcq0B2oOMq-vhSmG-ntJGJCf72hQwmwwlLhjtzQ4pjc0x3_HXofEp8nT2NHA7gYH3PjHcO2DKtPv8ZYLKpsVKNjIA"
          />
        </div>
      </header>

      <main className="pt-24 px-6 pb-24 max-w-lg mx-auto w-full">
        <section className="mb-12">
          <div className="flex items-center gap-8 mb-12">
            <div className="relative">
              <div className="w-24 h-24 overflow-hidden rounded-lg border-4 border-primary/10 p-1 bg-surface-container-lowest ambient-shadow ghost-border">
                <img 
                  alt="Alex Velocity" 
                  className="w-full h-full object-cover rounded-md grayscale" 
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuA-mIXqaRuN9ZRiYMY4DfCHPQJ50FjlNFIJ1e6HCZ9xYyyNEYP8ukpi8UI3LxbU4BzUqMKLobb2xJ2W_i0RuU3KJ72L-VuXAjLpXn8_si3JfAbRXfAh4I1mfxEI7YvQv88F-DEv-QWOieZdZLZJlFK4bS1NWtVahn8OBlnhTvbsZRkOHeaFihCsqZ6UhCktYmHhZiLFWTU7WZm338hVfQ6z6vnI6vw_x9cwRNMljSFMdJB5R929xOiQLYoJp0aDy2H2qwZGGl-OciE"
                />
              </div>
              <div className="absolute -bottom-2 -right-2 bg-primary text-white p-2.5 rounded-lg ambient-shadow">
                <Bolt size={16} />
              </div>
            </div>
            <div>
              <h1 className="text-4xl font-headline font-black tracking-tighter text-on-surface leading-none">
                ALEX <br/><span className="text-primary italic">VELOCITY</span>
              </h1>
              <div className="mt-4 p-4 bg-surface-container-lowest rounded-xl ghost-border ambient-shadow">
                <div className="flex items-center justify-between gap-6">
                  <div>
                    <span className="ui-label text-[7px] text-on-surface-variant/40 uppercase tracking-widest block mb-1">Tu Saldo</span>
                    <span className="text-xl font-headline font-black text-on-surface">Q12.50</span>
                  </div>
                  <button 
                    onClick={onNavigatePayments}
                    className="p-2.5 bg-primary text-white rounded-lg active:scale-90 transition-all shadow-lg shadow-primary/20"
                  >
                    <Plus size={16} strokeWidth={3} />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2 bg-primary p-10 rounded-lg flex flex-col justify-between min-h-[180px] ambient-shadow relative overflow-hidden group">
               <div className="absolute top-0 right-0 p-8 opacity-10">
                 <Bolt size={120} className="text-white" />
               </div>
              <div className="relative z-10">
                <div className="text-7xl font-headline font-normal text-white tracking-tighter leading-none italic">1,248</div>
                <div className="ui-label text-white/60 mt-4">Kilómetros Recorridos</div>
              </div>
            </div>
            <div className="bg-surface-container-low p-8 rounded-lg flex flex-col justify-between ambient-shadow ghost-border">
              <Route size={20} className="text-primary" />
              <div className="mt-8">
                <div className="text-4xl font-headline font-normal text-on-surface tracking-tighter leading-none">152</div>
                <div className="ui-label text-on-surface-variant/40 mt-2">Viajes Realizados</div>
              </div>
            </div>
            <div className="bg-surface-container-low p-8 rounded-lg flex flex-col justify-between ambient-shadow ghost-border">
              <Leaf size={20} className="text-secondary" />
              <div className="mt-8">
                <div className="text-4xl font-headline font-normal text-on-surface tracking-tighter leading-none">42<span className="text-xl">kg</span></div>
                <div className="ui-label text-on-surface-variant/40 mt-2">Mitigación de CO2</div>
              </div>
            </div>
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="ui-label text-on-surface-variant/40 mb-6 px-2 border-l-2 border-primary">Configuración</h2>
          {menuItems.map((item, idx) => (
            <button 
              key={idx}
              onClick={item.action}
              className="w-full group flex items-center justify-between p-6 bg-surface-container-low rounded-lg hover:bg-surface-container transition-all ambient-shadow ghost-border"
            >
              <div className="flex items-center gap-5">
                <div className="w-12 h-12 flex items-center justify-center bg-surface-container-lowest text-on-surface-variant rounded-lg group-hover:bg-primary group-hover:text-white transition-all ghost-border">
                  <item.icon size={18} />
                </div>
                <span className="ui-label text-on-surface">{item.label}</span>
              </div>
              <ChevronRight size={18} className="text-on-surface-variant/20 group-hover:text-primary transition-colors" />
            </button>
          ))}
        </section>

        <div className="mt-12 text-center pb-20">
          <button 
            onClick={onLogout}
            className="font-headline font-bold text-tertiary text-xs uppercase tracking-widest border-b-2 border-tertiary pb-1 hover:text-primary hover:border-primary transition-all"
          >
            Cerrar Sesión
          </button>
        </div>
      </main>
    </div>
  );
}
