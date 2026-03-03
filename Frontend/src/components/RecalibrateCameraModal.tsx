import { Camera, X } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface RecalibrateCameraModalProps {
  isVisible: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function RecalibrateCameraModal({ isVisible, onConfirm, onCancel }: RecalibrateCameraModalProps) {
  if (!isVisible) return null;

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
        >
          <motion.div
            initial={{ scale: 0.9, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.9, y: 20 }}
            className="bg-gradient-to-br from-slate-800 to-slate-900 border-2 border-purple-500/50 rounded-2xl shadow-2xl max-w-md w-full overflow-hidden"
          >
            {/* Header */}
            <div className="bg-gradient-to-r from-purple-600/20 via-indigo-600/20 to-purple-600/20 p-6 border-b border-purple-500/30">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0">
                  <div className="w-14 h-14 rounded-xl bg-purple-500/20 border-2 border-purple-400 flex items-center justify-center">
                    <Camera className="w-7 h-7 text-purple-400" strokeWidth={2.5} />
                  </div>
                </div>
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-white mb-1">
                    Recalibrer la caméra ?
                  </h2>
                  <p className="text-purple-300 text-sm font-medium">
                    Calibration du plateau d'échecs
                  </p>
                </div>
                <button
                  onClick={onCancel}
                  className="text-slate-400 hover:text-white transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>

            {/* Body */}
            <div className="p-6 space-y-4">
              <div className="bg-slate-700/50 border border-slate-600 rounded-xl p-4">
                <p className="text-white text-base leading-relaxed mb-3">
                  Vous êtes sur le point de <span className="text-purple-400 font-semibold">recalibrer la caméra</span>.
                </p>
                <p className="text-white text-sm leading-relaxed">
                  Cette action est nécessaire <span className="text-purple-400 font-semibold">uniquement si</span> la détection 
                  du plateau d'échecs est <span className="text-red-400 font-semibold">incorrecte ou imprécise</span>.
                </p>
              </div>

              <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4">
                <p className="text-white text-sm leading-relaxed font-medium">
                  ⚠️ Si la calibration actuelle fonctionne bien, il n'est pas nécessaire de la refaire.
                </p>
              </div>
            </div>

            {/* Footer */}
            <div className="bg-slate-800/50 px-6 py-4 flex gap-3">
              <button
                onClick={onCancel}
                className="flex-1 px-4 py-3 rounded-lg font-semibold text-slate-300 bg-slate-700 hover:bg-slate-600 border border-slate-600 hover:border-slate-500 transition-all"
              >
                Annuler
              </button>
              <button
                onClick={onConfirm}
                className="flex-1 px-4 py-3 rounded-lg font-semibold text-white bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 shadow-lg shadow-purple-500/30 transition-all"
              >
                Oui, recalibrer
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}