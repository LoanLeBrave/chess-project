import { History, User, Bot, RotateCcw } from 'lucide-react';
import type { ChessMove } from './GameScreen';

interface MoveHistoryProps {
  moves: ChessMove[];
  onGotoTurn?: (turn: number) => void;
  isRobotBusy?: boolean;
}

export function MoveHistory({ moves, onGotoTurn, isRobotBusy = false }: MoveHistoryProps) {
  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700 h-full flex flex-col">
      <h3 className="text-white font-semibold mb-3 flex items-center gap-2 text-sm">
        <div className="w-1 h-4 bg-cyan-400 rounded-full"></div>
        Historique
      </h3>

      <div className="space-y-2 overflow-y-auto custom-scrollbar flex-1">
        {moves.length === 0 ? (
          <div className="text-center py-6 text-slate-500">
            <History className="w-10 h-10 mx-auto mb-2 opacity-50" />
            <p className="text-xs">Aucun coup joué</p>
          </div>
        ) : (
          moves.slice().reverse().map((move, index) => {
            const originalIndex = moves.length - 1 - index;
            const moveNumber = moves.length - index;
            const isRobot = move.player === 'robot';
            // Cliquer = revenir à l'état AVANT ce coup (turn = originalIndex)
            const targetTurn = originalIndex;

            return (
              <div
                key={move.id}
                className={`
                  group flex items-center gap-2 p-2 rounded-lg relative
                  ${isRobot ? 'bg-cyan-900/20 border border-cyan-800/30' : 'bg-blue-900/20 border border-blue-800/30'}
                `}
              >
                <div className={`
                  w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0
                  ${isRobot ? 'bg-cyan-500/20 text-cyan-400' : 'bg-blue-500/20 text-blue-400'}
                `}>
                  {isRobot ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1">
                    <span className="text-slate-400 text-xs font-mono">#{moveNumber}</span>
                    <span className="text-white font-semibold text-xs truncate">
                      {move.piece} {move.from} → {move.to}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  {onGotoTurn && (
                    <button
                      onClick={() => onGotoTurn(targetTurn)}
                      disabled={isRobotBusy}
                      title={`Revenir avant ce coup (tour ${targetTurn})`}
                      className="
                        opacity-0 group-hover:opacity-100 transition-opacity
                        flex items-center gap-1 px-1.5 py-0.5 rounded text-xs
                        bg-amber-500/20 hover:bg-amber-500/40 text-amber-400
                        disabled:opacity-30 disabled:cursor-not-allowed
                      "
                    >
                      <RotateCcw className="w-3 h-3" />
                    </button>
                  )}
                  <div className="text-xs text-slate-500 font-mono">
                    {move.timestamp.toLocaleTimeString('fr-FR', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgb(51, 65, 85);
          border-radius: 2px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgb(100, 116, 139);
          border-radius: 2px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgb(148, 163, 184);
        }
      `}</style>
    </div>
  );
}