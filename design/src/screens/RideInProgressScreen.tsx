import { motion } from 'motion/react';
import { Battery, Bike, Navigation, MapPin, ChevronDown } from 'lucide-react';
import { useState } from 'react';

interface RideInProgressScreenProps {
  onEnd: () => void;
}

const STATIONS = [
  { id: '1', name: 'Estación Sol', distance: 2.4, time: 8 },
  { id: '2', name: 'Plaza Mayor', distance: 1.8, time: 6 },
  { id: '3', name: 'Terminal Norte', distance: 4.2, time: 15 },
  { id: '4', name: 'Puerto Central', distance: 3.1, time: 10 },
];

export default function RideInProgressScreen({ onEnd }: RideInProgressScreenProps) {
  const [selectedStation, setSelectedStation] = useState(STATIONS[0]);
  const [showSelector, setShowSelector] = useState(false);

  const estimatedCost = Math.ceil(selectedStation.distance * 2); // Q2 per min estimated

  return (
    <div className="min-h-screen bg-surface flex flex-col">
      <header className="fixed top-0 w-full max-w-lg z-50 flex justify-between items-center px-6 h-20 bg-surface/80 backdrop-blur-md">
        <div className="text-2xl font-headline font-black tracking-tighter text-primary">GIRO</div>
        <div className="flex items-center gap-3">
          <div className="bg-primary/10 text-primary px-3 py-1 rounded-full ui-label text-[8px] border border-primary/20">
            HOLD: Q50
          </div>
          <div className="w-8 h-8 rounded-full overflow-hidden grayscale">
            <img 
              alt="Profile" 
              className="w-full h-full object-cover" 
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuCB7B6Kmom9RPsZRFf1QqOHkVMAH4v2lJRWk_P5hBznE7Cy1lCk1DO9We78RnXOJNk6Fw3461IfKykOSmcyVKgwCrRTQmFSwqrfieomhh27UrTXaxddetg5A14L63d4_ZS_iBMpb8WKm0cJ3_wekU5K_SZMf-16a-Y1PHbpc6jQgtjKrwMBJwTcO4jiV6kCHDhQ-Tr6qFN_ylpSMCSQN_gyGEp3s-DGUkTbN8KTg-XhznZpLYyjW17_ZjCSchQYS7oeahCbRenAcNw"
            />
          </div>
        </div>
      </header>

      <main className="pt-24 px-6 pb-40 flex-grow flex flex-col">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <span className="w-1.5 h-1.5 bg-secondary rounded-full animate-pulse"></span>
            <span className="ui-label text-secondary">Viaje en Curso</span>
          </div>
          <h2 className="text-5xl font-headline font-black text-on-surface leading-[0.9] tracking-tighter">
            MI <br/>
            <span className="text-primary italic">VIAJE</span>
          </h2>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-surface-container p-6 rounded-lg flex flex-col justify-center items-center text-center ambient-shadow ghost-border relative overflow-hidden">
            <span className="ui-label text-on-surface-variant/40 mb-3 text-[9px]">TIEMPO</span>
            <div className="text-3xl font-headline font-black text-on-surface tracking-tighter leading-none tabular-nums">12:45</div>
          </div>
          <div className="bg-surface-container-low p-6 rounded-lg flex flex-col justify-center items-center text-center ambient-shadow ghost-border border-l-2 border-primary">
            <span className="ui-label text-on-surface-variant/40 mb-3 text-[9px]">ESTIMACIÓN</span>
            <div className="text-3xl font-headline font-black text-primary tracking-tighter leading-none tabular-nums italic">Q{estimatedCost}</div>
          </div>
        </div>

        <div className="relative w-full h-80 rounded-lg overflow-hidden mb-6 bg-surface-container-low ghost-border">
          <img 
            alt="Map view" 
            className="w-full h-full object-cover grayscale opacity-10" 
            src="https://lh3.googleusercontent.com/aida-public/AB6AXBvrGgqHj3MjAQ6gFH102lajasKejPk_DPZqMQa5q7o53eNKGi-hXTF7WPg3bAtWgQWnwvFc1HA6jqp7kNvtiUKRdmlBRUfFO2qMytQZnuAlt2lKk2V6llPytde0Lyhpt1-up1V2ySSt5jNt027sXQ6MJEfZ3JfHW90ah7pH7XVdV6nZxLM7q2_lH5lQ3EszQ2Eoiuks9kljMHDnqXRWh2YnQHxqI2SY3FI-3ZhwrYrXQLBDxB48vQ25SM4oMTPhmwVNdg3HdraNKM"
          />
          
          <div className="absolute inset-x-4 bottom-4 space-y-3">
            <div className="bg-surface/90 backdrop-blur-md p-5 rounded-lg ambient-shadow border border-white/20">
              <div className="flex justify-between items-center">
                <div 
                  className="flex items-center gap-3 cursor-pointer group"
                  onClick={() => setShowSelector(!showSelector)}
                >
                  <div className="bg-primary text-white p-2 rounded-md">
                    <MapPin size={16} />
                  </div>
                  <div>
                    <p className="ui-label text-on-surface text-[10px]">Destino Tentativo</p>
                    <p className="text-sm font-bold text-on-surface flex items-center gap-1">
                      {selectedStation.name}
                      <ChevronDown size={14} className={`text-primary transition-transform ${showSelector ? 'rotate-180' : ''}`} />
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="ui-label text-on-surface-variant/40 text-[9px]">DISTANCIA</p>
                  <p className="text-sm font-black text-primary">{selectedStation.distance}km</p>
                </div>
              </div>

              {showSelector && (
                <motion.div 
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  className="mt-6 pt-6 border-t border-outline-variant/10 space-y-2 max-h-40 overflow-y-auto"
                >
                  {STATIONS.map((station) => (
                    <button
                      key={station.id}
                      onClick={() => {
                        setSelectedStation(station);
                        setShowSelector(false);
                      }}
                      className={`w-full text-left p-3 rounded-md transition-all text-sm flex justify-between items-center ${selectedStation.id === station.id ? 'bg-primary/10 text-primary font-bold' : 'hover:bg-surface-container text-on-surface-variant'}`}
                    >
                      {station.name}
                      <span className="text-[10px] opacity-60">{station.distance}km</span>
                    </button>
                  ))}
                </motion.div>
              )}
            </div>
            
            <div className="bg-secondary/90 backdrop-blur-md px-6 py-3 rounded-lg flex items-center justify-between text-white ambient-shadow">
              <div className="flex items-center gap-2">
                <Navigation size={14} className="animate-pulse" />
                <span className="ui-label text-[9px]">DENTRO DE ÁREA OPERATIVA</span>
              </div>
              <span className="ui-label text-[8px] opacity-60">RETORNAR EN CUALQUIER ESTACIÓN</span>
            </div>
          </div>
        </div>

        <div className="bg-surface-container-low p-6 rounded-lg mb-8 ambient-shadow ghost-border border-t border-outline-variant/10">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-on-surface-variant/5 rounded text-on-surface-variant">
                <Bike size={18} />
              </div>
              <div>
                <p className="ui-label text-on-surface-variant/40 text-[9px] uppercase">Vehículo</p>
                <p className="text-sm font-bold text-on-surface">G SPRINT U842</p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-primary">
              <Battery size={16} />
              <span className="text-sm font-bold">84%</span>
            </div>
          </div>
        </div>

        <button 
          onClick={onEnd}
          className="w-full bg-primary text-white py-6 rounded-lg ui-label text-xs font-black uppercase tracking-widest active:scale-[0.98] transition-all ambient-shadow flex items-center justify-center gap-4 mt-auto"
        >
          Terminar y Pagar
        </button>
      </main>
    </div>
  );
}
