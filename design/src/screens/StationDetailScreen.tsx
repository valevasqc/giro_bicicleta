import { motion } from 'motion/react';
import { Bike, ParkingCircle, ArrowLeft, MapPin, LoaderCircle } from 'lucide-react';

interface StationDetailScreenProps {
  onBack: () => void;
  onUnlock: () => void;
}

export default function StationDetailScreen({ onBack, onUnlock }: StationDetailScreenProps) {
  return (
    <div className="min-h-screen bg-surface flex flex-col">
      <header className="fixed top-0 w-full max-w-lg z-50 flex items-center justify-between px-6 h-20 bg-surface/80 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-on-surface hover:text-primary active:scale-95 transition-all p-2 rounded-lg bg-surface-container-low">
            <ArrowLeft size={18} strokeWidth={3} />
          </button>
          <h1 className="ui-label text-on-surface-variant/40">Detalles de Estación</h1>
        </div>
        <div className="text-2xl font-headline font-black tracking-tighter text-primary">GIRO</div>
      </header>

      <main className="flex-grow pt-24 px-6 pb-32">
        {/* Map Snippet Section */}
        <motion.section 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="mb-12"
        >
          <div className="relative w-full h-56 bg-surface-container rounded-lg overflow-hidden ghost-border ambient-shadow">
            <img 
              className="w-full h-full object-cover grayscale opacity-20 mix-blend-multiply" 
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuCzy6MfRK74C1E7GkKKnXM322bqaNLaw1XUb913mzHUFyItcfGqFkT7REK9ztLFzkQVF9Ip9KUdElySrXc9cwMzSUlviqHB8R4h-Os66LZZQcxZzMf_2BMhSZpwuKh0h8zSnYQAnoe0WK6UvSl1WaRWjMbd96h-83KRc-V66kh6Zdaw6s9bTsanMIDgMVyiQU1oiyNZOzqM5JmZwJwcc0RUw_NepYagBcaGrawB1bYhPT4fEnp_aF1GOTWR6013MAvAMltcJ0CJijQ"
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="bg-primary text-white p-5 rounded-lg ambient-shadow">
                <Bike size={28} />
              </div>
            </div>
          </div>
        </motion.section>

        {/* Station Info Section */}
        <section className="mb-12">
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <span className="w-1.5 h-1.5 bg-tertiary rounded-full animate-pulse"></span>
              <span className="ui-label text-on-surface-variant/40">Estación Activa</span>
            </div>
            <h2 className="text-5xl md:text-6xl font-headline font-black text-on-surface leading-[0.9] tracking-tighter">
              PLAZA <br/>
              <span className="text-primary italic">CENTRAL</span>
            </h2>
            <div className="flex items-center gap-4 text-primary mt-4 py-4 border-t border-outline-variant/30">
              <MapPin size={20} />
              <p className="text-sm font-bold tracking-tight text-on-surface-variant">7a Avenida y 6a Calle, Zona 1</p>
            </div>
          </div>
        </section>

        {/* Availability Stats Section */}
        <section className="grid grid-cols-2 gap-4 mb-12">
          <div className="bg-surface-container-low p-8 rounded-lg flex flex-col items-start justify-between ambient-shadow ghost-border">
            <div className="w-10 h-10 rounded-lg bg-surface-container-lowest flex items-center justify-center mb-10 ghost-border">
              <Bike size={20} className="text-primary" />
            </div>
            <div>
              <div className="stat-value text-primary text-4xl">08</div>
              <p className="ui-label text-on-surface-variant/40 mt-3">Bicicletas Disponibles</p>
            </div>
          </div>

          <div className="bg-surface-container-low p-8 rounded-lg flex flex-col items-start justify-between ambient-shadow ghost-border">
            <div className="w-10 h-10 rounded-lg bg-surface-container-lowest flex items-center justify-center mb-10 ghost-border">
              <ParkingCircle size={20} className="text-on-surface-variant/40" />
            </div>
            <div>
              <div className="stat-value text-on-surface text-4xl">05</div>
              <p className="ui-label text-on-surface-variant/40 mt-3">Espacios Libres</p>
            </div>
          </div>
        </section>

        {/* Action Button Section */}
        <section className="space-y-4">
          <button 
            onClick={onUnlock}
            className="w-full bg-primary text-white py-6 rounded-lg ambient-shadow hover:bg-primary/90 active:scale-[0.98] flex flex-col items-center justify-center gap-1 transition-all"
          >
            <span className="ui-label text-xs font-black uppercase tracking-widest">Desbloquear Bicicleta</span>
            <span className="text-[8px] opacity-60 font-sans">Requiere autorización de Q50</span>
          </button>
          
          <div className="flex justify-between items-center p-6 bg-surface-container-low rounded-lg ghost-border">
            <span className="ui-label text-on-surface-variant/30 uppercase tracking-[0.3em]">Tarifa Operativa</span>
            <div className="flex items-baseline gap-2">
              <span className="text-[10px] text-primary font-black uppercase">GTQ</span>
              <span className="text-3xl font-headline font-normal text-on-surface tracking-tighter leading-none">1.25</span>
              <span className="text-[10px] text-on-surface-variant/40 italic font-bold">/m</span>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
