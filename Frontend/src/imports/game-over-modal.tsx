import { Trophy, Frown, TrendingDown, Clock, Target } from 'lucide-react';
import { motion } from 'motion/react';

interface GameOverModalProps {
  isVisible: boolean;
  result: 'win' | 'lose' | 'draw';
  acplScore: number;
  totalMoves: number;
  elapsedTime: number;
  playerName: string;
  onReturnToMenu: () => void;
  onViewLeaderboard: () => void;
}

export function GameOverModal({
  isVisible,
  result,
  acplScore,
  totalMoves,
  elapsedTime,
  playerName,
  onReturnToMenu,
  onViewLeaderboard
}: GameOverModalProps) {
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

  const resultConfig = {
    win: {
      title: 'Victoire !',
      subtitle: 'Félicitations, vous avez battu le robot',
      icon: Trophy,
      iconColor: 'text-yellow-400',
      bgGradient: 'from-yellow-500/20 to-amber-500/20',
      borderColor: 'border-yellow-500/50',
      glowColor: 'shadow-yellow-500/50'
    },
    lose: {
      title: 'Défaite',
      subtitle: 'Le robot a gagné cette fois-ci',
      icon: Frown,
      iconColor: 'text-red-400',
      bgGradient: 'from-red-500/20 to-orange-500/20',
      borderColor: 'border-red-500/50',
      glowColor: 'shadow-red-500/50'
    },
    draw: {
      title: 'Match nul',
      subtitle: 'Une partie serrée !',
      icon: Target,
      iconColor: 'text-blue-400',
      bgGradient: 'from-blue-500/20 to-cyan-500/20',
      borderColor: 'border-blue-500/50',
      glowColor: 'shadow-blue-500/50'
    }
  };

  const config = resultConfig[result];
  const Icon = config.icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <motion.div
        initial={{ scale: 0.8, opacity: 0, y: 50 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        transition={{ type: 'spring', damping: 15, stiffness: 300 }}
        className={`
          max-w-2xl w-full mx-4 bg-gradient-to-br ${config.bgGradient} 
          backdrop-blur-xl rounded-3xl border-2 ${config.borderColor}
          shadow-2xl ${config.glowColor} p-8
        `}
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
              <div className={`absolute inset-0 ${config.iconColor} blur-2xl opacity-60`}></div>
              <Icon className={`w-24 h-24 ${config.iconColor} relative`} strokeWidth={1.5} />
            </div>
          </motion.div>
          
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="text-5xl font-bold text-white mb-2"
          >
            {config.title}
          </motion.h1>
          
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="text-xl text-slate-300"
          >
            {config.subtitle}
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

        {/* Action Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="flex gap-4"
        >
          <button
            onClick={onViewLeaderboard}
            className="
              flex-1 px-6 py-4 rounded-xl font-bold text-lg
              bg-gradient-to-r from-yellow-500 to-amber-600
              hover:from-yellow-400 hover:to-amber-500
              text-white shadow-lg shadow-yellow-500/30
              hover:shadow-yellow-400/50 hover:scale-105
              transition-all duration-300
              flex items-center justify-center gap-2
            "
          >
            <Trophy className="w-5 h-5" />
            Voir le classement
          </button>

          <button
            onClick={onReturnToMenu}
            className="
              flex-1 px-6 py-4 rounded-xl font-bold text-lg
              bg-slate-700 hover:bg-slate-600
              text-white
              transition-all duration-300
              hover:scale-105
            "
          >
            Retour au menu
          </button>
        </motion.div>
      </motion.div>
    </div>
  );
}