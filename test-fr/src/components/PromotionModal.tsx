import { Crown, X } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface PromotionModalProps {
  isVisible: boolean;
  promotionSquare: string;
  promotionColor: 'white' | 'black';
  onConfirm: (piece: 'q' | 'r' | 'b' | 'n') => void;
}

export function PromotionModal({ isVisible, promotionSquare, promotionColor, onConfirm }: PromotionModalProps) {
  const pieces = [
    { code: 'q', name: 'Dame', symbol: '♕' },
    { code: 'r', name: 'Tour', symbol: '♖' },
    { code: 'b', name: 'Fou', symbol: '♗' },
    { code: 'n', name: 'Cavalier', symbol: '♘' },
  ] as const;

  return (
    <AnimatePresence>
      {isVisible && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="fixed inset-0 flex items-center justify-center z-50 p-4"
          >
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 border-2 border-cyan-500/50 rounded-2xl shadow-2xl max-w-md w-full p-6">
              {/* Header */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-yellow-500 to-amber-600 flex items-center justify-center shadow-lg">
                    <Crown className="w-7 h-7 text-white" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-white">Promotion du Pion</h2>
                    <p className="text-sm text-slate-400">Case {promotionSquare.toUpperCase()}</p>
                  </div>
                </div>
              </div>

              {/* Description */}
              <p className="text-slate-300 mb-6">
                Choisissez la pièce en laquelle vous souhaitez promouvoir votre pion :
              </p>

              {/* Piece Selection Grid */}
              <div className="grid grid-cols-2 gap-3">
                {pieces.map(piece => (
                  <button
                    key={piece.code}
                    onClick={() => onConfirm(piece.code)}
                    className="group relative bg-slate-700/50 hover:bg-slate-700 border-2 border-slate-600 hover:border-cyan-500 rounded-xl p-6 transition-all duration-300 transform hover:scale-105"
                  >
                    <div className="flex flex-col items-center gap-3">
                      <div className={`text-6xl ${promotionColor === 'white' ? 'text-slate-100' : 'text-slate-800'} drop-shadow-lg`}>
                        {piece.symbol}
                      </div>
                      <span className="text-white font-semibold group-hover:text-cyan-400 transition-colors">
                        {piece.name}
                      </span>
                    </div>
                    
                    {/* Hover effect */}
                    <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/0 to-blue-500/0 group-hover:from-cyan-500/10 group-hover:to-blue-500/10 rounded-xl transition-all duration-300" />
                  </button>
                ))}
              </div>

              {/* Info */}
              <div className="mt-6 bg-cyan-500/10 border border-cyan-500/30 rounded-xl p-3">
                <p className="text-cyan-300 text-sm text-center">
                  La dame est généralement le meilleur choix
                </p>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
