import { Bot, Trophy } from 'lucide-react';
import { Button } from './ui/button';

interface WelcomeScreenProps {
  onContinue: () => void;
  onViewLeaderboard: () => void;
}

export function WelcomeScreen({ onContinue, onViewLeaderboard }: WelcomeScreenProps) {
  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="max-w-2xl w-full text-center">
        {/* Logo et Titre */}
        <div className="flex items-center justify-center gap-4 mb-6">
          <div className="relative">
            <div className="absolute inset-0 bg-cyan-500 blur-3xl opacity-60"></div>
            <Bot className="w-24 h-24 text-cyan-400 relative" strokeWidth={1.5} />
          </div>
        </div>
        
        <h1 className="text-7xl font-bold bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent mb-4">
          Chess Robot UR7e
        </h1>
        
        <p className="text-2xl text-slate-400 mb-16">
          Affrontez l'intelligence artificielle sur un plateau d'échecs robotisé
        </p>

        {/* Bouton Central */}
        <div className="flex flex-col items-center gap-4">
          <Button
            onClick={onContinue}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onContinue(); }}
            size="lg"
            className="
              group relative px-16 py-8 rounded-2xl text-2xl font-bold
              bg-gradient-to-r from-cyan-500 to-blue-600
              hover:from-cyan-400 hover:to-blue-500
              text-white shadow-2xl shadow-cyan-500/50
              hover:shadow-cyan-400/70 hover:scale-105
              transition-all duration-300
              border-0
            "
          >
            Jouer
          </Button>

          {/* Bouton Classement */}
          <button
            onClick={onViewLeaderboard}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onViewLeaderboard(); }}
            className="flex items-center gap-2 text-slate-400 hover:text-yellow-400 transition-colors group px-6 py-3 rounded-lg hover:bg-slate-800/50"
          >
            <Trophy className="w-5 h-5 group-hover:scale-110 transition-transform" />
            <span className="font-medium">Voir le classement</span>
          </button>
        </div>

        {/* Sous-texte subtil */}
        <p className="text-sm text-slate-500 mt-12">
          Une expérience unique alliant stratégie et robotique
        </p>
      </div>
    </div>
  );
}
