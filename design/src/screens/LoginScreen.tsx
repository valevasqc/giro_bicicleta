import { motion } from 'motion/react';

interface LoginScreenProps {
  onLogin: () => void;
}

export default function LoginScreen({ onLogin }: LoginScreenProps) {
  return (
    <div className="min-h-screen bg-surface flex flex-col items-center justify-center p-6 relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(circle_at_10%_10%,_var(--tw-gradient-stops))] from-primary/5 via-transparent to-transparent pointer-events-none"></div>
      
      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-sm bg-surface-container-low p-10 rounded-lg ambient-shadow ghost-border relative z-10"
      >
        <div className="mb-16 text-center">
          <div className="text-4xl font-headline font-black tracking-tighter text-primary mb-2">GIRO</div>
          <p className="ui-label text-on-surface-variant/40">Iniciar Sesión</p>
        </div>

        <div className="space-y-12">
          <div className="relative group">
            <label className="font-headline font-bold text-[10px] uppercase tracking-widest text-on-surface-variant block mb-2 group-focus-within:text-primary transition-colors">
              USUARIO / EMAIL
            </label>
            <input 
              type="text" 
              placeholder="usuario@giro.app"
              className="w-full bg-transparent border-b-2 border-outline-variant py-3 text-sm focus:border-primary outline-none transition-all placeholder:text-on-surface-variant/20 font-sans font-medium"
            />
          </div>

          <div className="relative group">
            <label className="font-headline font-bold text-[10px] uppercase tracking-widest text-on-surface-variant block mb-2 group-focus-within:text-primary transition-colors">
              CLAVE DE ACCESO
            </label>
            <input 
              type="password" 
              placeholder="••••••••"
              className="w-full bg-transparent border-b-2 border-outline-variant py-3 text-sm focus:border-primary outline-none transition-all placeholder:text-on-surface-variant/20 font-sans font-medium"
            />
          </div>

          <button 
            onClick={onLogin}
            className="w-full bg-primary text-white py-6 rounded-lg text-xs font-ui font-black uppercase tracking-widest ambient-shadow hover:bg-primary/90 active:scale-[0.98] transition-all"
          >
            Entrar
          </button>
          
          <div className="text-center">
            <button className="ui-label text-on-surface-variant/40 hover:text-primary transition-colors underline underline-offset-8 decoration-outline-variant/30">
              Recuperar Clave
            </button>
          </div>
        </div>

        <div className="relative my-16">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t-2 border-outline-variant/30"></div>
          </div>
          <div className="relative flex justify-center text-[9px] font-black">
            <span className="bg-surface-container-low px-6 text-on-surface-variant/40 tracking-[0.4em] uppercase">Otras formas de sesión</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <button className="flex items-center justify-center gap-2 bg-surface-container p-4 rounded-lg ui-label hover:bg-surface-container-high transition-colors text-on-surface-variant">
            Apple Pay
          </button>
          <button className="flex items-center justify-center gap-2 bg-surface-container p-4 rounded-lg ui-label hover:bg-surface-container-high transition-colors text-on-surface-variant">
            Google Pay
          </button>
        </div>
      </motion.div>
      
      <p className="mt-12 ui-label text-on-surface-variant/30">
        ¿Eres nuevo? <button className="text-primary font-black hover:underline underline-offset-4">Crea una cuenta</button>
      </p>
    </div>
  );
}
