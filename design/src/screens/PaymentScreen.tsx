import { motion } from 'motion/react';
import { CreditCard, ArrowLeft, ShieldCheck, Apple, Chrome, Ticket, ChevronRight, Check } from 'lucide-react';
import { useState } from 'react';

interface PaymentScreenProps {
  onPay: () => void;
  onBack: () => void;
}

export default function PaymentScreen({ onPay, onBack }: PaymentScreenProps) {
  const [selectedMethod, setSelectedMethod] = useState<'card' | 'apple' | 'google' | 'code'>('card');
  const [promoCode, setPromoCode] = useState('');

  return (
    <div className="min-h-screen bg-surface flex flex-col">
      <header className="fixed top-0 w-full max-w-lg z-50 flex justify-between items-center px-6 h-20 bg-surface/80 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-on-surface hover:text-primary active:scale-90 transition-all p-2 rounded-lg bg-surface-container-lowest ghost-border">
            <ArrowLeft size={18} strokeWidth={2.5} />
          </button>
          <span className="ui-label text-on-surface opacity-60">PASARELA DE PAGO</span>
        </div>
        <div className="text-2xl font-headline font-black tracking-tighter text-primary">GIRO</div>
      </header>

      <main className="pt-24 px-6 pb-32 max-w-lg mx-auto w-full">
        <section className="mb-8">
          <div className="bg-surface-container-low p-8 rounded-2xl ambient-shadow ghost-border border-l-4 border-primary">
            <div className="flex justify-between items-start mb-6">
              <div>
                <span className="ui-label text-primary uppercase tracking-[0.2em] text-[10px] font-black">Tu Saldo Disponible</span>
                <div className="text-5xl font-headline font-black text-on-surface tracking-tighter mt-1 italic">Q12.50</div>
              </div>
              <div className="bg-primary/20 p-3 rounded-xl text-primary">
                <Ticket size={24} />
              </div>
            </div>
            <button 
              onClick={() => setSelectedMethod('code')}
              className="w-full bg-primary/10 text-primary py-3 rounded-lg ui-label text-[9px] font-black tracking-widest hover:bg-primary hover:text-white transition-all"
            >
              RECARGAR CON CÓDIGO
            </button>
          </div>
        </section>

        <section className="mb-10">
          <div className="flex items-center gap-3 mb-4">
            <span className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse"></span>
            <span className="ui-label text-on-surface-variant/40">Garantía de Viaje</span>
          </div>
          <h1 className="text-5xl font-headline font-black tracking-tighter text-on-surface leading-none mb-2 italic">AUTORIZAR</h1>
          <p className="ui-label text-primary">Depósito de seguridad para desbloqueo</p>
        </section>

        <section className="relative mb-8 pt-8">
          <div className="bg-primary p-12 rounded-2xl ambient-shadow text-center relative overflow-hidden">
            <div className="absolute -top-10 -right-10 opacity-20 rotate-12">
              <ShieldCheck size={180} className="text-white" />
            </div>
            <span className="relative z-10 ui-label text-white/60 mb-6 block uppercase tracking-[0.4em] text-[10px]">Depósito de Garantía</span>
            <div className="relative z-10 text-8xl font-headline font-black text-white tracking-tighter leading-none tabular-nums italic">
              50<span className="text-2xl ml-2 font-black not-italic opacity-50">QUETZALES</span>
            </div>
          </div>
          
          <div className="mt-8 px-8 py-4 bg-surface-container-low rounded-xl border border-outline-variant/10">
            <div className="flex gap-4 items-start">
              <div className="mt-1 text-primary">
                <ShieldCheck size={16} />
              </div>
              <p className="text-[10px] ui-label text-on-surface-variant/60 leading-relaxed font-medium">
                Se retendrán Q50 como garantía temporal. Al finalizar el viaje, el sistema cobrará automáticamente el monto exacto por los minutos de uso y liberará la diferencia a tu billetera.
              </p>
            </div>
          </div>
        </section>

        <div className="space-y-3 mb-8">
          <label className="font-headline font-bold text-[10px] uppercase tracking-widest text-on-surface-variant/40 block px-1">Métodos Rápidos</label>
          <div className="grid grid-cols-2 gap-4">
            <button 
              onClick={() => setSelectedMethod('apple')}
              className={`rounded-lg py-4 flex items-center justify-center gap-3 transition-all ambient-shadow ghost-border ${selectedMethod === 'apple' ? 'bg-primary text-white border-primary' : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'}`}
            >
              <Apple size={18} />
              <span className="ui-label text-[10px]">Apple Pay</span>
            </button>
            <button 
              onClick={() => setSelectedMethod('google')}
              className={`rounded-lg py-4 flex items-center justify-center gap-3 transition-all ambient-shadow ghost-border ${selectedMethod === 'google' ? 'bg-primary text-white border-primary' : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'}`}
            >
              <Chrome size={18} />
              <span className="ui-label text-[10px]">Google Pay</span>
            </button>
          </div>
        </div>

        <section className="space-y-4">
          <button 
            onClick={() => setSelectedMethod('card')}
            className={`w-full p-6 rounded-lg text-left transition-all ambient-shadow ghost-border flex items-center justify-between ${selectedMethod === 'card' ? 'bg-surface-container border-l-4 border-primary' : 'bg-surface-container-low hover:bg-surface-container'}`}
          >
            <div className="flex items-center gap-4">
              <div className={`p-2 rounded-md ${selectedMethod === 'card' ? 'bg-primary/10 text-primary' : 'bg-on-surface-variant/5 text-on-surface-variant/40'}`}>
                <CreditCard size={18} />
              </div>
              <div>
                <p className="text-sm font-bold text-on-surface tracking-widest">VISA • 8842</p>
                <p className="text-[10px] ui-label text-on-surface-variant/40 mt-1 uppercase leading-none">Pago Automático</p>
              </div>
            </div>
            {selectedMethod === 'card' && <Check size={16} className="text-primary" />}
          </button>

          <div className={`p-6 rounded-lg transition-all ambient-shadow ghost-border ${selectedMethod === 'code' ? 'bg-surface-container border-l-4 border-primary' : 'bg-surface-container-low group'}`}>
            <button 
              onClick={() => setSelectedMethod('code')}
              className="w-full flex items-center justify-between text-left"
            >
              <div className="flex items-center gap-4">
                <div className={`p-2 rounded-md ${selectedMethod === 'code' ? 'bg-primary/10 text-primary' : 'bg-on-surface-variant/5 text-on-surface-variant/40'}`}>
                  <Ticket size={18} />
                </div>
                <div>
                  <p className="text-sm font-bold text-on-surface tracking-widest">CANJEAR TARJETA</p>
                  <p className="text-[10px] ui-label text-on-surface-variant/40 mt-1 uppercase leading-none">Pagar con Quetzales</p>
                </div>
              </div>
              {selectedMethod === 'code' && <Check size={16} className="text-primary" />}
            </button>
            
            {selectedMethod === 'code' && (
              <motion.div 
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                className="overflow-hidden"
              >
                <div className="pt-6 mt-4 border-t border-outline-variant/10 space-y-4">
                  <input 
                    type="text" 
                    placeholder="CÓDIGO DE TARJETA FÍSICA"
                    value={promoCode}
                    onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
                    className="w-full bg-transparent border-b-2 border-primary/20 focus:border-primary py-3 text-xs font-bold tracking-[0.2em] outline-none transition-all placeholder:text-on-surface-variant/20 uppercase"
                  />
                  <p className="text-[9px] ui-label text-primary font-medium leading-tight">Al ingresar el código se acreditarán los Quetzales necesarios para completar este viaje.</p>
                </div>
              </motion.div>
            )}
          </div>
        </section>

        <div className="mt-12 flex items-center justify-center gap-3 text-on-surface-variant/20">
          <ShieldCheck size={14} />
          <span className="ui-label text-on-surface-variant/20 font-normal">Transacción Encriptada: 256-bit AES</span>
        </div>

        <div className="mt-12">
          <button 
            onClick={onPay}
            className="w-full bg-primary text-white py-6 rounded-lg ui-label text-[11px] active:scale-[0.98] transition-all ambient-shadow flex items-center justify-center gap-4"
          >
            {selectedMethod === 'code' && !promoCode ? 'Ingresar Código para Continuar' : 'Confirmar e Iniciar Viaje'}
          </button>
        </div>
      </main>
    </div>
  );
}

