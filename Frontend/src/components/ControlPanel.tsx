import { Play, Pause, Square, RotateCcw, Home, LayoutGrid, Loader2 } from 'lucide-react';
import type { GameState } from '../App';

interface ControlPanelProps {
  gameState: GameState;
  onPause: () => void;
  onStop: () => void;
  onNewGame: () => void;
  onReplaceBoard: () => void;
  isReplacingBoard?: boolean;
}

export function ControlPanel({
  gameState,
  onPause,
  onStop,
  onNewGame,
  onReplaceBoard,
  isReplacingBoard = false,
}: ControlPanelProps) {
  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
        <button
          onClick={onPause}
          className={`
            flex items-center justify-center gap-2 px-3 py-2 rounded-lg font-semibold text-sm
            transition-all duration-200
            ${gameState === 'playing' 
              ? 'bg-yellow-500 hover:bg-yellow-400 text-slate-900' 
              : 'bg-green-500 hover:bg-green-400 text-white'
            }
            shadow-lg hover:scale-105
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
          onClick={onNewGame}
          className="
            flex items-center justify-center gap-2 px-3 py-2 rounded-lg font-semibold text-sm
            bg-blue-500 hover:bg-blue-400 text-white
            transition-all duration-200 shadow-lg hover:scale-105
          "
        >
          <RotateCcw className="w-4 h-4" />
          Nouveau
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
              ? 'bg-purple-700/50 text-purple-300 cursor-not-allowed'
              : 'bg-purple-600 hover:bg-purple-500 text-white hover:scale-105'
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
      </div>
    </div>
  );
}