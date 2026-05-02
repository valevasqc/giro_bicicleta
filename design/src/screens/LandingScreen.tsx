import { motion } from 'motion/react';
import { ArrowRight } from 'lucide-react';

interface LandingScreenProps {
  onStart: () => void;
}

export default function LandingScreen({ onStart }: LandingScreenProps) {
  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-black flex flex-col">
      {/* Background Video */}
      <div className="absolute inset-0 z-0">
        <video 
          autoPlay 
          muted 
          loop 
          playsInline
          className="w-full h-full object-cover opacity-60 scale-105"
        >
          <source src="https://assets.mixkit.co/videos/preview/mixkit-man-riding-a-bicycle-in-the-city-at-night-41018-large.mp4" type="video/mp4" />
        </video>
        <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/80"></div>
      </div>

      {/* Top Left Logo */}
      <header className="relative z-10 p-10">
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="text-4xl font-headline font-black tracking-tighter text-white"
        >
          GIRO
        </motion.div>
      </header>

      {/* Centered Bottom Button */}
      <main className="relative z-10 mt-auto flex flex-col items-center pb-12 px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="w-full max-w-xs text-center"
        >
          <button 
            onClick={onStart}
            className="w-full bg-white text-black py-6 rounded-full font-ui font-black text-xs uppercase tracking-[0.3em] hover:bg-primary hover:text-white transition-all active:scale-95 shadow-2xl"
          >
            Iniciar Sesión
          </button>
        </motion.div>
      </main>
    </div>
  );
}
