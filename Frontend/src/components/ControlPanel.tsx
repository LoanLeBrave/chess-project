import { Play, Pause, Square, RotateCcw, Loader2, Wifi } from 'lucide-react';
import type { GameState } from '../App';

interface ControlPanelProps {
  gameState: GameState;
  onPause: () => void;
  onStop: () => void;
  onNewGame: () => void;
  onReconnect: () => void;
  isReconnecting?: boolean;
}

export function ControlPanel({
  gameState,
  onPause,
  onStop,
  onNewGame,
  onReconnect,
  isReconnecting = false,
}: ControlPanelProps) {
  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <button
          onClick={onStop}
          className="
            flex items-center justify-center gap-2 px-3 py-2 rounded-lg font-semibold text-sm
            bg-red-500 hover:bg-red-400 text-white
            transition-all duration-200 shadow-lg hover:scale-105
          "
        >
          <Square className="w-4 h-4" fill="currentColor" />
          Arrêter
        </button>

        <button
          onClick={onPause}
          className={`
            flex items-center justify-center gap-2 px-3 py-2 rounded-lg font-semibold text-sm
            transition-all duration-200 shadow-lg hover:scale-105
            ${gameState === 'playing'
              ? 'bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-white shadow-amber-500/30'
              : 'bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-400 hover:to-emerald-400 text-white shadow-green-500/30'
            }
          `}
        >
          {gameState === 'playing' ? (
            <>
              <Pause className="w-4 h-4" fill="currentColor" />
              Pause
            </>
          ) : (
            <>
              <Play className="w-4 h-4" fill="currentColor" />
              Reprendre
            </>
          )}
        </button>

        <button
          onClick={onNewGame}
          className="
            flex items-center justify-center gap-2 px-3 py-2 rounded-lg font-semibold text-sm
            bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white
            transition-all duration-200 shadow-lg hover:scale-105
          "
        >
          <RotateCcw className="w-4 h-4" />
          Nouvelle Partie
        </button>

        <button
          onClick={onReconnect}
          disabled={isReconnecting}
          className={`
            flex items-center justify-center gap-2 px-3 py-2 rounded-lg font-semibold text-sm
            transition-all duration-200 shadow-lg
            ${isReconnecting
              ? 'bg-slate-700/50 text-slate-400 cursor-not-allowed'
              : 'bg-slate-600 hover:bg-slate-500 text-white hover:scale-105'
            }
          `}
          title="Reconnecte le robot après un blocage ou un timeout"
        >
          {isReconnecting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Connexion…
            </>
          ) : (
            <>
              <Wifi className="w-4 h-4" />
              Reconnecter
            </>
          )}
        </button>
      </div>
    </div>
  );
}