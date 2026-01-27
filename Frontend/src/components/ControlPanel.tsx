import { Play, Pause, Square, RotateCcw, Home } from 'lucide-react';
import type { GameState } from '../App';

interface ControlPanelProps {
  gameState: GameState;
  onPause: () => void;
  onStop: () => void;
  onNewGame: () => void;
}

export function ControlPanel({ gameState, onPause, onStop, onNewGame }: ControlPanelProps) {
  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
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
      </div>
    </div>
  );
}