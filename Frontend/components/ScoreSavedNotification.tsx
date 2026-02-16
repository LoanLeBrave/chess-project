import { CheckCircle, X } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface ScoreSavedNotificationProps {
  isVisible: boolean;
  onClose: () => void;
  playerName: string;
  acplScore: number;
  moves: number;
}

export function ScoreSavedNotification({ 
  isVisible, 
  onClose, 
  playerName, 
  acplScore, 
  moves 
}: ScoreSavedNotificationProps) {
  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: -100, scale: 0.8 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -50, scale: 0.9 }}
          transition={{ type: 'spring', damping: 20, stiffness: 300 }}
          className="fixed top-6 left-1/2 -translate-x-1/2 z-50"
        >
          <div className="
            bg-gradient-to-r from-green-500/20 to-emerald-500/20
            backdrop-blur-xl rounded-2xl border-2 border-green-500/50
            shadow-2xl shadow-green-500/30 p-4 pr-6
            flex items-center gap-4 min-w-[400px]
          ">
            {/* Icon */}
            <div className="relative">
              <div className="absolute inset-0 bg-green-400 blur-xl opacity-60"></div>
              <div className="w-12 h-12 bg-green-500/20 rounded-full flex items-center justify-center relative">
                <CheckCircle className="w-6 h-6 text-green-400" strokeWidth={2.5} />
              </div>
            </div>

            {/* Content */}
            <div className="flex-1">
              <p className="text-white font-bold text-lg mb-1">
                Score enregistré !
              </p>
              <div className="text-sm text-slate-300">
                <span className="text-green-400 font-semibold">{playerName}</span>
                {' · ACPL: '}
                <span className="text-cyan-400 font-semibold">{acplScore}</span>
                {' · Coups: '}
                <span className="text-purple-400 font-semibold">{moves}</span>
              </div>
            </div>

            {/* Close Button */}
            <button
              onClick={onClose}
              className="
                w-8 h-8 rounded-lg bg-slate-700/50 hover:bg-slate-600
                flex items-center justify-center
                transition-all hover:scale-110
                text-slate-400 hover:text-white
              "
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
