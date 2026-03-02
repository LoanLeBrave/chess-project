import { AlertTriangle, TrendingDown, Clock, Target, MessageSquare } from 'lucide-react';
import { motion } from 'motion/react';

interface GameOverModalAbandonedProps {
  isVisible: boolean;
  acplScore: number;
  totalMoves: number;
  elapsedTime: number;
  playerName: string;
  onContinue: () => void;
}

export function GameOverModalAbandoned({
  isVisible,
  acplScore,
  totalMoves,
  elapsedTime,
  playerName,
  onContinue
}: GameOverModalAbandonedProps) {
  if (!isVisible) return null;

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getACPLColor = (acpl: number) => {
    if (acpl <= 20) return 'text-green-400';
    if (acpl <= 40) return 'text-cyan-400';
    if (acpl <= 60) return 'text-yellow-400';
    return 'text-orange-400';
  };

  const getACPLLabel = (acpl: number) => {
    if (acpl <= 20) return 'Excellent';
    if (acpl <= 40) return 'Très bon';
    if (acpl <= 60) return 'Bon';
    return 'Correct';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <motion.div
        initial={{ scale: 0.8, opacity: 0, y: 50 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        transition={{ type: 'spring', damping: 15, stiffness: 300 }}
        className="
          max-w-2xl w-full mx-4 bg-gradient-to-br from-amber-500/20 to-orange-500/20
          backdrop-blur-xl rounded-3xl border-2 border-amber-500/50
          shadow-2xl shadow-amber-500/50 p-8
        "
      >
        {/* Icon & Title */}
        <div className="text-center mb-8">
          <motion.div
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ delay: 0.2, type: 'spring', damping: 10 }}
            className="inline-block mb-4"
          >
            <div className="relative">
              <div className="absolute inset-0 text-amber-400 blur-2xl opacity-60"></div>
              <AlertTriangle className="w-24 h-24 text-amber-400 relative" strokeWidth={1.5} />
            </div>
          </motion.div>
          
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="text-5xl font-bold text-white mb-2"
          >
            Partie arrêtée
          </motion.h1>
          
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="text-xl text-slate-300"
          >
            Vos statistiques ont été enregistrées
          </motion.p>
        </div>

        {/* Stats Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="grid grid-cols-3 gap-4 mb-8"
        >
          {/* ACPL Score */}
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
            <div className="flex items-center justify-center gap-2 mb-2">
              <TrendingDown className="w-4 h-4 text-cyan-400" />
              <span className="text-slate-400 text-sm font-medium">Score ACPL</span>
            </div>
            <div className="text-center">
              <div className={`text-3xl font-bold ${getACPLColor(acplScore)}`}>
                {acplScore}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                {getACPLLabel(acplScore)}
              </div>
            </div>
          </div>

          {/* Total Moves */}
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Target className="w-4 h-4 text-purple-400" />
              <span className="text-slate-400 text-sm font-medium">Coups joués</span>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-purple-400">
                {totalMoves}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                mouvements
              </div>
            </div>
          </div>

          {/* Time */}
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Clock className="w-4 h-4 text-cyan-400" />
              <span className="text-slate-400 text-sm font-medium">Temps</span>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-cyan-400 font-mono">
                {formatTime(elapsedTime)}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                écoulé
              </div>
            </div>
          </div>
        </motion.div>

        {/* Player Info */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="bg-slate-800/30 rounded-xl p-4 border border-slate-700 mb-6 text-center"
        >
          <p className="text-slate-400 text-sm">
            Partie enregistrée pour <span className="text-white font-semibold">{playerName}</span>
          </p>
        </motion.div>

        {/* Action Button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
        >
          <button
            onClick={onContinue}
            className="
              w-full px-6 py-4 rounded-xl font-bold text-lg
              bg-gradient-to-r from-cyan-500 to-blue-600
              hover:from-cyan-400 hover:to-blue-500
              text-white shadow-lg shadow-cyan-500/30
              hover:shadow-cyan-400/50 hover:scale-105
              transition-all duration-300
              flex items-center justify-center gap-2
            "
          >
            <MessageSquare className="w-5 h-5" />
            Continuer vers le feedback
          </button>
        </motion.div>
      </motion.div>
    </div>
  );
}
