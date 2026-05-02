import { motion } from 'motion/react';
import { ArrowLeft, MessageSquare, Phone, Mail, HelpCircle, ChevronRight, FileText, Globe } from 'lucide-react';

interface SupportScreenProps {
  onBack: () => void;
}

export default function SupportScreen({ onBack }: SupportScreenProps) {
  const categories = [
    { label: 'Problemas con la Bicicleta', icon: HelpCircle, description: 'Frenos, llantas o problemas mecánicos' },
    { label: 'Pagos y Facturación', icon: Globe, description: 'Dudas con tus Quetzales o cargos' },
    { label: 'App y Tecnología', icon: Globe, description: 'Errores al desbloquear o reportar' },
  ];

  const contactMethods = [
    { label: 'Chat en Vivo', icon: MessageSquare, sub: 'Respuesta en < 5 min', color: 'bg-primary' },
    { label: 'WhatsApp GIRO', icon: Phone, sub: 'Soporte 24/7', color: 'bg-secondary' },
    { label: 'Email', icon: Mail, sub: 'soporte@giro.app', color: 'bg-tertiary' },
  ];

  return (
    <div className="min-h-screen bg-surface flex flex-col">
      <header className="fixed top-0 w-full max-w-lg z-50 flex justify-between items-center px-6 h-20 bg-surface/80 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-on-surface hover:text-primary active:scale-95 transition-all p-2 rounded-lg bg-surface-container-low">
            <ArrowLeft size={18} strokeWidth={3} />
          </button>
          <h1 className="ui-label text-on-surface-variant/40 uppercase tracking-[0.2em]">Ayuda y Soporte</h1>
        </div>
        <div className="text-2xl font-headline font-black tracking-tighter text-primary">GIRO</div>
      </header>

      <main className="pt-24 px-6 pb-20 max-w-lg mx-auto w-full">
        <section className="mb-10">
          <h2 className="text-4xl font-headline font-black text-on-surface tracking-tighter leading-none mb-4">¿EN QUÉ PODEMOS <span className="text-primary italic">AYUDARTE?</span></h2>
          <p className="ui-label text-on-surface-variant/40">Estamos aquí para que tu movilidad no se detenga.</p>
        </section>

        <section className="grid grid-cols-1 gap-4 mb-10">
          {categories.map((cat, i) => (
            <button key={i} className="flex items-center justify-between p-6 bg-surface-container-low rounded-xl ambient-shadow ghost-border hover:bg-surface-container transition-all text-left">
              <div className="flex items-center gap-5">
                <div className="p-3 bg-surface rounded-lg text-primary">
                  <cat.icon size={20} />
                </div>
                <div>
                  <p className="font-bold text-on-surface">{cat.label}</p>
                  <p className="text-[10px] ui-label text-on-surface-variant/40 mt-1">{cat.description}</p>
                </div>
              </div>
              <ChevronRight size={18} className="text-on-surface-variant/20" />
            </button>
          ))}
        </section>

        <section className="mb-10">
          <span className="ui-label text-on-surface-variant/40 mb-6 block uppercase tracking-widest text-[9px]">Canales Directos</span>
          <div className="grid grid-cols-1 gap-3">
            {contactMethods.map((method, i) => (
              <button key={i} className="flex items-center gap-6 p-6 bg-surface-container-low rounded-xl ghost-border overflow-hidden relative group">
                <div className={`absolute left-0 top-0 w-1 h-full ${method.color}`}></div>
                <div className={`p-3 rounded-lg text-white ${method.color}`}>
                  <method.icon size={18} />
                </div>
                <div>
                  <p className="font-bold text-on-surface text-sm uppercase tracking-widest">{method.label}</p>
                  <p className="text-[10px] ui-label text-on-surface-variant/40 mt-1">{method.sub}</p>
                </div>
              </button>
            ))}
          </div>
        </section>

        <footer className="pt-10 border-t border-outline-variant/10">
          <div className="space-y-4">
            <button className="flex items-center gap-3 text-on-surface-variant/40 hover:text-primary transition-colors">
              <FileText size={16} />
              <span className="ui-label text-[10px] uppercase">Términos y Condiciones</span>
            </button>
            <button className="flex items-center gap-3 text-on-surface-variant/40 hover:text-primary transition-colors">
              <FileText size={16} />
              <span className="ui-label text-[10px] uppercase">Política de Privacidad</span>
            </button>
          </div>
        </footer>
      </main>
    </div>
  );
}
