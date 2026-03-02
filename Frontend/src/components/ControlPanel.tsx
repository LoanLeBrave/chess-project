import { Play, Pause, Square, RotateCcw, Home, LayoutGrid, Loader2, Wifi } from 'lucide-react';
import type { GameState } from '../App';

interface ControlPanelProps {
  gameState: GameState;
  onPause: () => void;
  onStop: () => void;
  onNewGame: () => void;
  onReplaceBoard: () => void;
  onReconnect: () => void;
  isReplacingBoard?: boolean;
  isReconnecting?: boolean;
}

export function ControlPanel({
  gameState,
  onPause,
  onStop,
  onNewGame,
  onReplaceBoard,
  onReconnect,
  isReplacingBoard = false,
  isReconnecting = false,
}: ControlPanelProps) {
  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
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
          className="
            flex items-center justify-center gap-2 px-3 py-2 rounded-lg font-semibold text-sm
            bg-yellow-500 hover:bg-yellow-400 text-slate-900
            transition-all duration-200 shadow-lg hover:scale-105
          "
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
          onClick={onStop}
          className="
            flex items-center justify-center gap-2 px-3 py-2 rounded-lg font-semibold text-sm
            bg-slate-600 hover:bg-slate-500 text-white
            transition-all duration-200 shadow-lg hover:scale-105
          "
        >
          <Home className="w-4 h-4" />
          Menu
        </button>

        <button
          onClick={onReplaceBoard}
          disabled={isReplacingBoard}
          className={`
            flex items-center justify-center gap-2 px-3 py-2 rounded-lg font-semibold text-sm
            transition-all duration-200 shadow-lg
            ${isReplacingBoard
              ? 'bg-slate-700/50 text-slate-400 cursor-not-allowed'
              : 'bg-slate-600 hover:bg-slate-500 text-white hover:scale-105'
            }
          `}
          title="Replace toutes les pieces a leur position initiale via le robot"
        >
          {isReplacingBoard ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Replacement…
            </>
          ) : (
            <>
              <LayoutGrid className="w-4 h-4" />
              Replacer
            </>
          )}
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