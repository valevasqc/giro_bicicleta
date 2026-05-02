import { motion, AnimatePresence } from 'motion/react';
import { History, Plus, ChevronRight, Timer, Route, ArrowLeft, MapPin, CreditCard, X } from 'lucide-react';
import { useState } from 'react';

interface TripsHistoryScreenProps {
  onNewTrip: () => void;
}

export default function TripsHistoryScreen({ onNewTrip }: TripsHistoryScreenProps) {
  const [selectedTrip, setSelectedTrip] = useState<any>(null);

  const trips = [
    { id: 1, date: '12 OCT 2023', duration: '25 min', distance: '5.8 km', cost: '35', origin: 'Plaza Mayor', dest: 'Estación Sol', img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCQLLQ6wvMl-zS3eZ2Zj0YXWVx_xVEsHwr-UeXUGAQHtO4kF3qciWqOrxX_Q6-GbF9brTyMnYSYoduN5LceWWzTUoa2noaoOMBxRIQfw8cYrCNCrcWC3IykCiOB0phqiRIfudjWBY5tWVUs7018V4fE4fhVzKOlgvNiaccpy4u7oIf3GaogYI6_5Ck4_40nz8CgrvieS3gTfdA7VACRd-zcpx9Kt9UekD7IlF1TVcGuOo9mMyYb2ZMzkoptzi4GO4lPwscUqz1wkQM' },
    { id: 2, date: '10 OCT 2023', duration: '12 min', distance: '2.4 km', cost: '15', origin: 'Terminal Norte', dest: 'Plaza Mayor', img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCQLLQ6wvMl-zS3eZ2Zj0YXWVx_xVEsHwr-UeXUGAQHtO4kF3qciWqOrxX_Q6-GbF9brTyMnYSYoduN5LceWWzTUoa2noaoOMBxRIQfw8cYrCNCrcWC3IykCiOB0phqiRIfudjWBY5tWVUs7018V4fE4fhVzKOlgvNiaccpy4u7oIf3GaogYI6_5Ck4_40nz8CgrvieS3gTfdA7VACRd-zcpx9Kt9UekD7IlF1TVcGuOo9mMyYb2ZMzkoptzi4GO4lPwscUqz1wkQM' },
    { id: 3, date: '08 OCT 2023', duration: '48 min', distance: '14.2 km', cost: '82', origin: 'Estación Sol', dest: 'Puerto Central', isLongest: true, img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCQLLQ6wvMl-zS3eZ2Zj0YXWVx_xVEsHwr-UeXUGAQHtO4kF3qciWqOrxX_Q6-GbF9brTyMnYSYoduN5LceWWzTUoa2noaoOMBxRIQfw8cYrCNCrcWC3IykCiOB0phqiRIfudjWBY5tWVUs7018V4fE4fhVzKOlgvNiaccpy4u7oIf3GaogYI6_5Ck4_40nz8CgrvieS3gTfdA7VACRd-zcpx9Kt9UekD7IlF1TVcGuOo9mMyYb2ZMzkoptzi4GO4lPwscUqz1wkQM' },
  ];

  return (
    <div className="min-h-screen bg-surface flex flex-col">
      <header className="fixed top-0 w-full max-w-lg z-50 flex justify-between items-center px-6 h-20 bg-surface/80 backdrop-blur-md">
        <div className="text-2xl font-headline font-black tracking-tighter text-primary">GIRO</div>
        <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-primary/20 p-0.5">
          <img 
            alt="Profile photo" 
            className="w-full h-full object-cover rounded-full grayscale" 
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuD-brkzuQuzj1GPfmlNy6GJfBipk9BnS-N6uSo19wn0JpwArKbz2dfDvPSpKimIUKDuGQAd2l0KBY1vqNtBJgUHYiZVGlpjuGdS5ny4vxm4MGFNeOoD3L1d-PC5SBR3zsOFgsVPTH-q8Axlbh2IVjo6Fa12SaGyQ2W7YwU1LmsI_ADvgvL3XxfedqGhXew1W9kaLR7i_CH2HWcp8Mpbm7fLyipVYX3gA7BXoxMfHuNOQSIWr9Rj2av1QPoWmqzf2B0QpXgPquTK5Vw"
          />
        </div>
      </header>

      <main className="pt-24 px-6 pb-48 max-w-lg mx-auto w-full">
        <div className="mb-12">
          <div className="flex items-center gap-3 mb-4">
            <span className="w-1.5 h-1.5 bg-primary rounded-full"></span>
            <span className="ui-label text-on-surface-variant/40">Registro de Actividad</span>
          </div>
          <h2 className="text-5xl font-headline font-black text-on-surface tracking-tighter leading-none mb-2">MIS VIAJES</h2>
        </div>

        <div className="space-y-4">
          {trips.map((trip, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1 }}
              onClick={() => setSelectedTrip(trip)}
              className="group bg-surface-container-low rounded-lg p-6 flex gap-5 items-center transition-all hover:bg-surface-container cursor-pointer ambient-shadow relative overflow-hidden ghost-border"
            >
              {trip.isLongest && (
                <div className="absolute top-0 right-0 bg-primary text-white px-3 py-1.5 ui-label text-[8px] rounded-bl-lg">
                  NUEVO RÉCORD
                </div>
              )}
              <div className="w-20 h-20 rounded-lg overflow-hidden shrink-0 ambient-shadow ghost-border bg-surface-container">
                <img className="w-full h-full object-cover grayscale opacity-30 block group-hover:opacity-60 transition-opacity" src={trip.img} alt="ruta" />
              </div>
              <div className="flex-1">
                <span className="ui-label text-on-surface-variant/40 mb-2 block">{trip.date}</span>
                <div className="flex items-center gap-6 text-on-surface font-headline font-normal text-xl tracking-tighter">
                  <div className="flex items-center gap-2">
                    <Timer size={16} className="text-primary" />
                    <span>{trip.duration}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Route size={16} className="text-secondary" />
                    <span>{trip.distance}</span>
                  </div>
                </div>
              </div>
              <ChevronRight size={18} className="text-on-surface-variant/20 group-hover:text-primary group-hover:translate-x-1 transition-all" />
            </motion.div>
          ))}
        </div>

        <div className="mt-16 bg-primary text-surface rounded-lg p-10 flex flex-col gap-12 ambient-shadow ghost-border overflow-hidden relative">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2"></div>
          <div className="relative z-10">
            <div className="flex items-center gap-3 mb-6">
              <span className="w-1.5 h-1.5 bg-surface rounded-full animate-pulse"></span>
              <span className="ui-label text-surface/60">Balance Semanal</span>
            </div>
            <p className="text-7xl font-headline font-normal tracking-tighter leading-none mb-4 italic">23.5km</p>
            <p className="ui-label text-surface/40">Distancia total recorrida</p>
          </div>
          
          <div className="flex gap-2 items-end h-24 relative z-10">
            {[40, 60, 30, 90, 70, 100, 50].map((h, i) => (
              <motion.div 
                key={i} 
                initial={{ height: 0 }}
                animate={{ height: `${h}%` }}
                className={`flex-1 rounded-sm transition-all duration-500 ${i === 5 ? 'bg-secondary ambient-shadow' : 'bg-surface/20'}`} 
              />
            ))}
          </div>
        </div>
      </main>

      <div className="fixed bottom-24 left-0 w-full z-40">
        <div className="max-w-lg mx-auto px-6">
          <button 
            onClick={onNewTrip}
            className="w-full bg-primary text-white py-6 rounded-lg ui-label text-[11px] ambient-shadow hover:bg-primary/90 transition-all flex items-center justify-center gap-4"
          >
            Nuevo Viaje
            <Plus size={18} />
          </button>
        </div>
      </div>

      <AnimatePresence>
        {selectedTrip && (
          <motion.div 
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed inset-0 z-[100] bg-surface flex flex-col p-6 overflow-y-auto"
          >
            <div className="flex justify-between items-center mb-10">
              <button 
                onClick={() => setSelectedTrip(null)}
                className="p-3 bg-surface-container-low rounded-lg text-on-surface-variant active:scale-90 transition-all"
              >
                <X size={20} />
              </button>
              <h3 className="ui-label text-on-surface-variant/40 uppercase tracking-widest text-[9px]">Detalles del Viaje</h3>
              <div className="w-10"></div>
            </div>

            <div className="mb-10 text-center">
              <span className="ui-label text-primary mb-4 block uppercase leading-none">{selectedTrip.date}</span>
              <h4 className="text-6xl font-headline font-black text-on-surface tracking-tighter italic leading-none">{selectedTrip?.cost && `Q${selectedTrip.cost}`}</h4>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-8">
              <div className="bg-surface-container-low p-6 rounded-lg ghost-border">
                <Timer size={18} className="text-primary mb-3" />
                <p className="ui-label text-on-surface-variant/40 text-[9px] mb-1 uppercase">TIEMPO</p>
                <p className="text-xl font-headline font-bold text-on-surface">{selectedTrip.duration}</p>
              </div>
              <div className="bg-surface-container-low p-6 rounded-lg ghost-border">
                <Route size={18} className="text-secondary mb-3" />
                <p className="ui-label text-on-surface-variant/40 text-[9px] mb-1 uppercase">DISTANCIA</p>
                <p className="text-xl font-headline font-bold text-on-surface">{selectedTrip.distance}</p>
              </div>
            </div>

            <div className="bg-surface-container-low p-8 rounded-lg mb-8 ghost-border">
              <div className="space-y-8 relative">
                <div className="absolute left-1.5 top-2 bottom-2 w-0.5 bg-outline-variant/30"></div>
                <div className="flex gap-6 relative z-10">
                  <div className="w-3 h-3 rounded-full bg-primary mt-1 border-2 border-surface"></div>
                  <div>
                    <p className="ui-label text-on-surface-variant/40 text-[9px] mb-1 uppercase font-normal">ORIGEN</p>
                    <p className="text-sm font-bold text-on-surface">{selectedTrip.origin}</p>
                  </div>
                </div>
                <div className="flex gap-6 relative z-10">
                  <div className="w-3 h-3 rounded-full bg-secondary mt-1 border-2 border-surface"></div>
                  <div>
                    <p className="ui-label text-on-surface-variant/40 text-[9px] mb-1 uppercase font-normal">DESTINO</p>
                    <p className="text-sm font-bold text-on-surface">{selectedTrip.dest}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-auto pt-10">
              <button 
                className="w-full py-6 flex items-center justify-center gap-4 ui-label text-primary hover:bg-primary/5 rounded-lg transition-colors"
                onClick={() => setSelectedTrip(null)}
              >
                Cerrar Detalle
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
