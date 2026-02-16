import { User, Clock } from 'lucide-react';

interface PlayerTurnStatusProps {
  isPlayerTurn: boolean;
}

export function PlayerTurnStatus({ isPlayerTurn }: PlayerTurnStatusProps) {
  return (
    <div className={`
      rounded-xl p-4 border-2 transition-all duration-300
      ${isPlayerTurn 
        ? 'bg-green-900/30 border-green-500 shadow-lg shadow-green-500/30' 
        : 'bg-red-900/30 border-red-500 shadow-lg shadow-red-500/30'
      }
    `}>
      <div className="flex items-center gap-3">
        <div className={`
          w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0
          ${isPlayerTurn ? 'bg-green-500' : 'bg-red-500'}
        `}>
          {isPlayerTurn ? (
            <User className="w-6 h-6 text-white" strokeWidth={2} />
          ) : (
            <Clock className="w-6 h-6 text-white" strokeWidth={2} />
          )}
        </div>
        <div className="flex-1">
          <div className={`text-lg font-bold ${isPlayerTurn ? 'text-green-400' : 'text-red-400'}`}>
            {isPlayerTurn ? 'À vous de jouer !' : 'Attendez votre tour'}
          </div>
          <div className="text-slate-400 text-xs">
            {isPlayerTurn 
              ? 'Sélectionnez une pièce blanche' 
              : 'Le robot joue son coup'
            }
          </div>
        </div>
        {!isPlayerTurn && (
          <div className="flex gap-1">
            <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse"></div>
            <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
            <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
          </div>
        )}
      </div>
    </div>
  );
}