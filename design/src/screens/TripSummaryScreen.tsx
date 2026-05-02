import { motion } from 'motion/react';
import { Timer, MapPin, Share2, CheckCircle2, ArrowRight } from 'lucide-react';

interface TripSummaryScreenProps {
  onFinish: () => void;
}

export default function TripSummaryScreen({ onFinish }: TripSummaryScreenProps) {
  return (
    <div className="min-h-screen bg-surface flex flex-col">
      <header className="fixed top-0 w-full max-w-lg z-50 flex justify-between items-center px-6 h-20 bg-surface/80 backdrop-blur-md">
        <div className="text-2xl font-headline font-black tracking-tighter text-primary">GIRO</div>
        <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-primary/20 p-0.5">
          <img 
            className="w-full h-full object-cover rounded-full grayscale" 
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuBPFCyVwFwA4V61ynFia96W8geW6HtdF6sSbHEYi1HUYrjlSxWWp3CDLT4PRupBRUwfL2ea1bChMOjwV8R0oj0W0FvqGNuaItYqN7BXfExjBLPICMnBQgYsBEpd2lnpIhvaMxNI0vkXbqD8EWhSQqupphgCywpo2nA_w2JdYCmLZPilZgvCPTRRUH_YZpv983Sy2WFN6n_Wm8uO4j0vEGa1got74bPTymEzDLVkWs-RF_v0HiPOUnx52y4JqOqoVfp3q1_w5IflaK4"
            alt="User"
          />
        </div>
      </header>

      <main className="max-w-xl mx-auto px-6 pt-24 pb-32">
        <section className="mb-10 text-center">
          <div className="flex items-center justify-center gap-3 mb-6">
            <span className="w-1.5 h-1.5 bg-tertiary rounded-full"></span>
            <span className="ui-label text-on-surface-variant/40">¡Viaje Finalizado!</span>
          </div>
          <h1 className="text-5xl font-headline font-black tracking-tighter text-on-surface leading-none mb-4">RESUMEN DEL<br/><span className="text-primary italic">VIAJE</span></h1>
          <p className="ui-label text-primary">Ahorraste: 1.2kg de CO2</p>
        </section>

        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="col-span-2 bg-surface-container p-10 flex flex-col items-center justify-center text-center ambient-shadow ghost-border rounded-lg relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <CheckCircle2 size={60} />
            </div>
            <span className="ui-label text-on-surface-variant/40 mb-3 uppercase tracking-[0.3em]">Costo del Viaje</span>
            <span className="text-6xl font-headline font-black text-primary tracking-tighter leading-none tabular-nums italic">Q35</span>
            
            <div className="mt-10 w-full pt-8 border-t border-outline-variant/10 grid grid-cols-2 gap-8">
              <div className="text-left">
                <p className="ui-label text-[9px] text-on-surface-variant/40 mb-1">DEPÓSITO INICIAL</p>
                <p className="text-xl font-headline font-normal text-on-surface">Q50</p>
              </div>
              <div className="text-right">
                <p className="ui-label text-[9px] text-primary mb-1">REEMBOLSO</p>
                <p className="text-xl font-headline font-normal text-primary">Q15</p>
              </div>
            </div>
          </div>
          <div className="bg-surface-container-low rounded-lg p-6 flex flex-col ambient-shadow ghost-border">
            <div className="mb-6 text-primary"><Timer size={18} /></div>
            <span className="ui-label text-on-surface-variant/40 mb-1 text-[9px]">Duración</span>
            <span className="text-2xl font-headline font-normal text-on-surface tracking-tighter">25 min</span>
          </div>
          <div className="bg-surface-container-low rounded-lg p-6 flex flex-col ambient-shadow ghost-border">
            <div className="mb-6 text-primary"><MapPin size={18} /></div>
            <span className="ui-label text-on-surface-variant/40 mb-1 text-[9px]">Distancia</span>
            <span className="text-2xl font-headline font-normal text-on-surface tracking-tighter">5.8 km</span>
          </div>
        </div>

        <div className="bg-surface-container-low rounded-lg overflow-hidden mb-12 ambient-shadow ghost-border">
          <div className="h-48 w-full bg-surface-container relative">
            <img 
              className="w-full h-full object-cover opacity-20 grayscale mix-blend-multiply" 
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuCP4U02j673sKVtVSYAqR_KuzEj20veNyU0m6u1XgyOPY4BanSsvjHsMNz_Rwz9Cv48lZgOqQaVkK8gckALuAqksEBXsAiQEc2rpjrXgNrrqjATdkMvVxXlZQM43zn11w9DYbFEQIGqRI4ot_AnHGEMiH9mkEPkFuo2JCJ18KI74F1ir4FZNJ4Kff4CAoxbQwe1u0yygEdaTwhNEldYZCagbkXuX0ePok1esjQkdCg2JyPecZeYVnJzB_Yjp6TOXP5TSSpB6Vi9SCs"
              alt="Map"
            />
            <div className="absolute bottom-6 left-6 flex items-center gap-2 bg-surface/90 backdrop-blur-md px-4 py-2 rounded-lg ghost-border ambient-shadow">
              <CheckCircle2 size={16} className="text-primary" />
              <span className="ui-label text-primary">Viaje Guardado</span>
            </div>
          </div>
          <div className="p-10">
            <h3 className="ui-label text-on-surface-variant/40 mb-8 px-2 border-l-2 border-primary">Recorrido Finalizado</h3>
            <div className="space-y-10">
              <div className="flex gap-6">
                <div className="flex flex-col items-center">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                  <div className="w-0.5 h-12 bg-outline-variant/30" />
                  <div className="w-1.5 h-1.5 bg-primary/20 rounded-full border border-primary" />
                </div>
                <div className="flex flex-col justify-between py-0">
                  <div>
                    <p className="ui-label text-on-surface-variant/40 mb-1">Origen</p>
                    <p className="text-sm font-bold text-on-surface">Calle Mayor 45, Centro</p>
                  </div>
                  <div>
                    <p className="ui-label text-on-surface-variant/40 mb-1">Destino</p>
                    <p className="text-sm font-bold text-on-surface">Estación Sol</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <button 
            onClick={onFinish}
            className="w-full bg-primary text-white py-6 rounded-lg flex items-center justify-center gap-4 active:scale-[0.98] transition-all ambient-shadow ui-label text-xs"
          >
            Listo
            <ArrowRight size={20} />
          </button>
          <button className="w-full bg-surface-container-lowest text-on-surface py-5 rounded-lg flex items-center justify-center gap-3 active:scale-[0.98] transition-all ambient-shadow ui-label text-[10px]">
            <Share2 size={18} className="text-primary" />
            Compartir Resumen
          </button>
        </div>
      </main>
    </div>
  );
}
