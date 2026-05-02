import { motion } from 'motion/react';
import { ArrowLeft, CreditCard, Plus, ChevronRight, Check, Trash2, Ticket } from 'lucide-react';
import { useState } from 'react';

interface PaymentMethodsScreenProps {
  onBack: () => void;
}

export default function PaymentMethodsScreen({ onBack }: PaymentMethodsScreenProps) {
  const [methods, setMethods] = useState([
    { id: '1', type: 'visa', last4: '8842', isDefault: true },
    { id: '2', type: 'mastercard', last4: '1234', isDefault: false },
  ]);

  const [promoCode, setPromoCode] = useState('');

  return (
    <div className="min-h-screen bg-surface flex flex-col">
      <header className="fixed top-0 w-full max-w-lg z-50 flex justify-between items-center px-6 h-20 bg-surface/80 backdrop-blur-md">
        <div className="text-2xl font-headline font-black tracking-tighter text-primary">GIRO</div>
        <div className="w-10 h-10"></div>
      </header>

      <main className="pt-24 px-6 pb-24 max-w-lg mx-auto w-full">
        <section className="mb-10">
          <div className="flex items-center gap-3 mb-6">
            <span className="w-1.5 h-1.5 bg-primary rounded-full"></span>
            <span className="ui-label text-on-surface-variant/40">Mi Billetera</span>
          </div>

          <div className="bg-surface-container-low p-8 rounded-2xl ambient-shadow ghost-border mb-8 border-l-4 border-primary">
            <span className="ui-label text-on-surface-variant/40 block mb-3 uppercase tracking-widest text-[10px] font-black">Saldo disponible</span>
            <div className="text-5xl font-headline font-black text-on-surface tracking-tighter italic">Q50.00</div>
            
            <div className="mt-8 pt-6 border-t border-outline-variant/10">
              <label className="font-headline font-bold text-[10px] uppercase tracking-widest text-on-surface-variant block mb-4">
                CANJEAR TARJETA PREPAGO
              </label>
              <div className="flex gap-3">
                <div className="relative flex-1">
                  <Ticket className="absolute left-3 top-1/2 -translate-y-1/2 text-primary" size={16} />
                  <input 
                    type="text" 
                    value={promoCode}
                    onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
                    placeholder="INGRESAR CÓDIGO"
                    className="w-full bg-surface-container-lowest border border-outline-variant/20 rounded-xl py-3 pl-10 pr-4 text-[7px] focus:border-primary outline-none transition-all placeholder:text-on-surface-variant/20 font-bold tracking-widest"
                  />
                </div>
                <button className="bg-primary text-white px-6 py-3 rounded-xl ui-label text-[10px] hover:bg-primary/90 transition-all font-black shadow-lg shadow-primary/20">
                  Cargar
                </button>
              </div>
            </div>
          </div>
        </section>

        <section className="mb-10">
          <div className="flex items-center gap-3 mb-6">
            <span className="w-1.5 h-1.5 bg-on-surface-variant/20 rounded-full"></span>
            <span className="ui-label text-on-surface-variant/40">Mis Tarjetas</span>
          </div>

          <div className="space-y-4">
            {methods.map((method) => (
              <div 
                key={method.id}
                className="bg-surface-container-low p-6 rounded-lg flex items-center justify-between ambient-shadow ghost-border group hover:bg-surface-container transition-all"
              >
                <div className="flex items-center gap-5">
                  <div className="w-14 h-10 bg-surface-container-lowest rounded flex items-center justify-center ghost-border">
                    <CreditCard size={18} className="text-on-surface-variant/40" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-on-surface flex items-center gap-2">
                      •••• •••• •••• {method.last4}
                      {method.isDefault && (
                        <span className="text-[8px] px-2 py-0.5 bg-primary/10 text-primary rounded-full uppercase tracking-widest font-black">Principal</span>
                      )}
                    </p>
                    <p className="text-[10px] ui-label text-on-surface-variant/40 mt-1 uppercase">{method.type}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button className="p-2 text-on-surface-variant/20 hover:text-primary transition-colors">
                    <Check size={16} className={method.isDefault ? 'opacity-100' : 'opacity-0'} />
                  </button>
                  <button className="p-2 text-on-surface-variant/20 hover:text-primary transition-colors">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}

            <button className="w-full p-6 border-2 border-dashed border-outline-variant/30 rounded-lg flex items-center justify-center gap-4 text-on-surface-variant/40 hover:border-primary hover:text-primary transition-all group">
              <Plus size={18} className="group-hover:scale-110 transition-transform" />
              <span className="ui-label">Agregar Nueva Tarjeta</span>
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}
