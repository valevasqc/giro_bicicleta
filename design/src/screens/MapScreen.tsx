import { motion, useMotionValue, useSpring, AnimatePresence } from 'motion/react';
import { MapPin, Battery, Zap, ArrowRight, Navigation, Plus, Minus, Layers, Search } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';

interface Station {
  id: string;
  name: string;
  bikes: number;
  distance: string;
  district: string;
  x: number;
  y: number;
}

const STATIONS: Station[] = [
  { id: '1', name: 'Estación Sol', bikes: 5, distance: '150m', district: 'Distrito Central', x: 450, y: 300 },
  { id: '2', name: 'Plaza Mayor', bikes: 12, distance: '400m', district: 'Casco Antiguo', x: 200, y: 150 },
  { id: '3', name: 'Terminal Norte', bikes: 0, distance: '1.2km', district: 'Zona Industrial', x: 600, y: 100 },
  { id: '4', name: 'Puerto Central', bikes: 8, distance: '850m', district: 'Muelle Sur', x: 300, y: 550 },
  { id: '5', name: 'UFM Tech', bikes: 3, distance: '2.1km', district: 'Zona 10', x: 750, y: 450 },
];

interface MapScreenProps {
  onSelectStation: () => void;
}

export default function MapScreen({ onSelectStation }: MapScreenProps) {
  const [selectedStation, setSelectedStation] = useState<Station | null>(null);
  const [zoom, setZoom] = useState(1);
  const [isListView, setIsListView] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleZoom = (delta: number) => {
    setZoom(prev => Math.min(Math.max(prev + delta, 0.5), 2.5));
  };

  return (
    <div className="relative h-screen w-full overflow-hidden bg-surface">
      {/* Top Header */}
      <header className="fixed top-0 w-full max-w-lg z-50 flex justify-between items-center px-6 h-20 bg-surface/80 backdrop-blur-md">
        <div className="font-headline font-black tracking-tighter text-2xl text-primary">GIRO</div>
        <div className="flex items-center gap-4">
          <button 
            onClick={() => setIsListView(!isListView)}
            className="bg-primary/10 px-4 py-2 rounded-full border border-primary/20 flex items-center gap-2 text-primary hover:bg-primary hover:text-white transition-all active:scale-95"
          >
            {isListView ? <MapPin size={14} /> : <Layers size={14} />}
            <span className="ui-label text-[10px] font-black tracking-widest">{isListView ? 'VER MAPA' : 'VER LISTA'}</span>
          </button>
          <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-primary/20 p-0.5">
            <img 
              alt="User profile" 
              className="w-full h-full object-cover rounded-full grayscale" 
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuCCKAV7E3GSQ_nejoYFWmxfPXgQPSIccHdKHndzRh13iZKR0jiHzzzS7a2AsvmDZT16fb9pf4D7jgUyRsj6VY-QCuqcIUsQD10FLjW8IEFskxmqHeMCpkVHshIva0e5ro_SIYiTmkyf75CLOOc1Xe-0_i257DzmynNoyYTORRMAZaVUe3jkSWS0Z3oWAwHtV6YIHXN8gYIMWRbr9SfPmxxjWdgBwVQgBk3douNHR2Enko3yZrvUYpFQ8QAUtmJmSURLgZnkYRw5YHU"
            />
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="absolute inset-0 pt-20">
        <AnimatePresence mode="wait">
          {!isListView ? (
            <motion.div 
              key="map-view"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="relative h-full w-full"
            >
              {/* Map Canvas (Draggable Area) */}
              <div className="absolute inset-0 z-0 touch-none" ref={containerRef}>
        <motion.div 
          drag
          dragConstraints={containerRef}
          style={{ scale: zoom }}
          className="relative w-[2000px] h-[2000px] flex items-center justify-center cursor-grab active:cursor-grabbing"
          initial={{ x: -800, y: -800 }}
          onClick={() => setSelectedStation(null)}
        >
          {/* Map Base Texture */}
          <div className="absolute inset-0 bg-[#f8f9fa]">
            <img 
              src="https://images.unsplash.com/photo-1524661135-423995f22d0b?auto=format&fit=crop&q=80&w=2000" 
              className="w-full h-full object-cover opacity-10 grayscale"
              alt="Map base"
            />
            <div className="absolute inset-0 pattern-dots text-on-surface-variant/5"></div>
            <svg width="100%" height="100%" className="opacity-10 absolute inset-0">
              <defs>
                <pattern id="grid" width="100" height="100" patternUnits="userSpaceOnUse">
                  <path d="M 100 0 L 0 0 0 100" fill="none" stroke="currentColor" strokeWidth="0.5"/>
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#grid)" />
            </svg>
          </div>

          {/* District Labels */}
          <div className="absolute top-[300px] left-[400px] ui-label text-on-surface-variant/20 text-3xl font-black uppercase tracking-[0.5em] pointer-events-none italic">Centro</div>
          <div className="absolute top-[600px] left-[200px] ui-label text-on-surface-variant/20 text-3xl font-black uppercase tracking-[0.5em] pointer-events-none italic">Zona Sur</div>
          <div className="absolute top-[400px] left-[800px] ui-label text-on-surface-variant/20 text-3xl font-black uppercase tracking-[0.5em] pointer-events-none italic">Norte</div>

          {/* Interactive Markers */}
          {STATIONS.map((station) => (
            <motion.div 
              key={station.id}
              className="absolute"
              style={{ left: station.x, top: station.y }}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              whileHover={{ scale: 1.1 }}
            >
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedStation(station);
                }}
                className={`relative group h-12 w-12 flex items-center justify-center transition-all ${selectedStation?.id === station.id ? 'z-50' : 'z-10'}`}
              >
                <div className={`absolute -inset-6 rounded-full blur-2xl transition-opacity duration-500 ${selectedStation?.id === station.id ? 'bg-primary/30 opacity-100' : 'bg-primary/5 opacity-0 group-hover:opacity-100'}`}></div>
                
                <div className={`relative p-3 rounded-xl ambient-shadow ghost-border border-b-2 transition-all ${selectedStation?.id === station.id ? 'bg-primary text-white scale-125 border-primary shadow-primary/20' : 'bg-surface-container-low text-on-surface hover:bg-surface border-outline-variant/20'}`}>
                  <MapPin size={20} fill="currentColor" fillOpacity={selectedStation?.id === station.id ? 0.3 : 0} />
                </div>
                
                {/* Station Health Indicator */}
                <div className={`absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full border-2 border-surface flex items-center justify-center ${station.bikes > 0 ? 'bg-success' : 'bg-error'}`}>
                  <div className={`w-1 h-1 bg-white rounded-full ${station.bikes > 0 ? 'animate-pulse' : ''}`}></div>
                </div>

                {/* Quick Info Popup on hover/selected */}
                <AnimatePresence>
                  {selectedStation?.id === station.id && (
                    <motion.div 
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 10 }}
                      className="absolute -top-10 left-1/2 -translate-x-1/2 bg-on-surface text-surface py-1 px-3 rounded-full ui-label text-[8px] whitespace-nowrap tracking-widest font-black"
                    >
                      {station.bikes} DISPONIBLES
                    </motion.div>
                  )}
                </AnimatePresence>
              </button>
            </motion.div>
          ))}
        </motion.div>
      </div>

      {/* Floating Detail Card */}
      <AnimatePresence mode="wait">
        {selectedStation && (
          <motion.div 
            key={selectedStation.id}
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 50, opacity: 0 }}
            className="absolute bottom-24 left-6 right-6 max-w-[320px] mx-auto z-40 pointer-events-none"
          >
            <div className="bg-surface/90 backdrop-blur-[12px] p-5 rounded-xl ambient-shadow outline outline-1 outline-outline-variant/10 pointer-events-auto">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className={`w-1 h-1 rounded-full ${selectedStation.bikes > 0 ? 'bg-primary' : 'bg-error'}`}></span>
                    <span className={`ui-label text-[7px] uppercase tracking-widest font-black ${selectedStation.bikes > 0 ? 'text-primary' : 'text-error'}`}>
                      {selectedStation.bikes > 0 ? 'Disponible' : 'Sin Unidades'}
                    </span>
                  </div>
                  <h2 className="text-xl font-headline font-black tracking-tight text-on-surface leading-none">{selectedStation.name}</h2>
                  <div className="flex items-center gap-1.5 mt-2">
                    <Navigation size={10} className="text-on-surface-variant/40" />
                    <span className="ui-label text-on-surface-variant/40 text-[7px] uppercase tracking-widest">{selectedStation.district}</span>
                  </div>
                </div>
                <div className="bg-surface-container-low px-3 py-2 rounded-lg text-center min-w-[60px] ghost-border">
                  <span className="stat-value text-on-surface text-lg font-headline block leading-none">{selectedStation.bikes}</span>
                  <span className="ui-label text-on-surface-variant/40 text-[6px] uppercase tracking-widest block font-black mt-1">Unidades</span>
                </div>
              </div>

              <div className="mb-5">
                <div className="bg-surface-container-low p-3 rounded-lg flex flex-col gap-1 border border-outline-variant/5">
                  <div className="flex items-center justify-between">
                    <p className="ui-label text-on-surface-variant/40 text-[7px] uppercase tracking-widest font-black">Tarifa</p>
                    <p className="text-[7px] ui-label text-on-surface-variant/30">{selectedStation.distance}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="bg-primary/10 p-1.5 rounded text-primary">
                      <Zap size={12} fill="currentColor" fillOpacity={0.2} />
                    </div>
                    <p className="text-sm font-headline font-black text-on-surface tracking-tight">Q1.25 <span className="text-[7px] ui-label text-on-surface-variant/40 font-normal tracking-normal italic">/ MIN</span></p>
                  </div>
                </div>
              </div>

              <button 
                onClick={onSelectStation}
                className="w-full bg-primary text-white py-4 rounded-lg font-ui font-black text-[10px] uppercase tracking-widest ambient-shadow active:scale-[0.98] transition-all flex items-center justify-center gap-3"
              >
                Explorar Estación
                <ArrowRight size={14} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Map Controls */}
      <div className="absolute right-6 top-1/2 -translate-y-1/2 flex flex-col gap-4 z-30">
        <button 
          onClick={() => setZoom(1)}
          className="w-14 h-14 bg-surface/90 backdrop-blur-md rounded-2xl ambient-shadow ghost-border flex items-center justify-center text-primary active:scale-90 transition-all border-b-4 border-primary/20"
        >
          <Navigation size={22} className="stroke-[2.5px]" />
        </button>
        <div className="flex flex-col bg-surface/90 backdrop-blur-md rounded-2xl ambient-shadow ghost-border overflow-hidden border-b-4 border-outline-variant/20">
          <button 
            onClick={() => handleZoom(0.2)}
            className="w-14 h-14 flex items-center justify-center text-on-surface hover:bg-primary hover:text-white transition-all text-2xl font-black"
          >
            <Plus size={20} strokeWidth={4} />
          </button>
          <div className="h-px bg-outline-variant/20 mx-3"></div>
          <button 
            onClick={() => handleZoom(-0.2)}
            className="w-14 h-14 flex items-center justify-center text-on-surface hover:bg-primary hover:text-white transition-all text-2xl font-black"
          >
            <Minus size={20} strokeWidth={4} />
          </button>
        </div>
        <button className="w-14 h-14 bg-surface/90 backdrop-blur-md rounded-2xl ambient-shadow ghost-border flex items-center justify-center text-on-surface-variant hover:text-primary active:scale-90 transition-all">
          <Layers size={22} />
        </button>
      </div>
    </motion.div>
  ) : (
    <motion.div 
      key="list-view"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="h-full w-full overflow-y-auto px-6 pb-32 pt-8"
    >
      <div className="grid gap-4">
        {STATIONS.map((station) => (
          <button 
            key={station.id}
            onClick={() => {
              setSelectedStation(station);
              setIsListView(false);
            }}
            className="bg-surface-container-low p-6 rounded-2xl flex items-center justify-between ambient-shadow ghost-border hover:bg-surface transition-all active:scale-[0.98] text-left"
          >
            <div className="flex items-center gap-4">
              <div className={`p-4 rounded-xl ${station.bikes > 0 ? 'bg-primary/10 text-primary' : 'bg-on-surface-variant/5 text-on-surface-variant'}`}>
                <MapPin size={24} />
              </div>
              <div>
                <h3 className="text-xl font-headline font-black text-on-surface leading-tight tracking-tight">{station.name}</h3>
                <p className="ui-label text-[9px] text-on-surface-variant/40 uppercase tracking-widest mt-1">{station.district} • {station.distance}</p>
              </div>
            </div>
            <div className="text-right">
              <span className={`text-2xl font-headline font-black block leading-none ${station.bikes > 0 ? 'text-primary' : 'text-on-surface-variant/20'}`}>
                {station.bikes}
              </span>
              <span className="ui-label text-[7px] text-on-surface-variant/40 uppercase tracking-widest block mt-1">Bicicletas</span>
            </div>
          </button>
        ))}
      </div>
    </motion.div>
  )}
</AnimatePresence>
</div>

      <div className="fixed top-24 left-6 right-6 z-40 max-w-[320px] mx-auto">
        {!isListView && (
          <div className="bg-surface/90 backdrop-blur-md ghost-border rounded-xl p-3 flex items-center gap-3 ambient-shadow">
            <Search size={14} className="text-primary" />
            <input 
              type="text" 
              placeholder="BUSCAR DESTINO..." 
              className="bg-transparent border-none outline-none ui-label text-[9px] flex-1 placeholder:text-on-surface-variant/20 uppercase tracking-widest"
            />
          </div>
        )}
      </div>
    </div>
  );
}
