import { useState } from 'react';
import { Play, Zap, Brain, Crown, Bot } from 'lucide-react';
import type { DifficultyLevel } from '../App';

interface StartScreenProps {
  onStartGame: (difficulty: DifficultyLevel) => void;
}

export function StartScreen({ onStartGame }: StartScreenProps) {
  const [selectedDifficulty, setSelectedDifficulty] = useState<DifficultyLevel>('beginner');

  const difficulties = [
    {
      id: 'beginner' as DifficultyLevel,
      label: 'Débutant',
      icon: Zap,
      description: 'Parfait pour commencer',
      color: 'from-green-500 to-emerald-600',
      borderColor: 'border-green-500',
      glowColor: 'shadow-green-500/50'
    },
    {
      id: 'intermediate' as DifficultyLevel,
      label: 'Intermédiaire',
      icon: Brain,
      description: 'Un défi équilibré',
      color: 'from-blue-500 to-cyan-600',
      borderColor: 'border-blue-500',
      glowColor: 'shadow-blue-500/50'
    },
    {
      id: 'advanced' as DifficultyLevel,
      label: 'Difficile',
      icon: Crown,
      description: 'Pour les experts',
      color: 'from-purple-500 to-pink-600',
      borderColor: 'border-purple-500',
      glowColor: 'shadow-purple-500/50'
    }
  ];

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="max-w-5xl w-full">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-4 mb-4">
            <div className="relative">
              <div className="absolute inset-0 bg-cyan-500 blur-xl opacity-50"></div>
              <Bot className="w-16 h-16 text-cyan-400 relative" strokeWidth={1.5} />
            </div>
            <h1 className="text-6xl font-bold bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
              Chess Robot UR7e
            </h1>
          </div>
          <p className="text-xl text-slate-400">
            Affrontez l'intelligence artificielle sur un plateau d'échecs robotisé
          </p>
        </div>

        {/* Difficulty Selection */}
        <div className="mb-10">
          <h2 className="text-2xl font-semibold text-white mb-6 text-center">
            Choisissez votre niveau
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {difficulties.map((diff) => {
              const Icon = diff.icon;
              const isSelected = selectedDifficulty === diff.id;
              return (
                <button
                  key={diff.id}
                  onClick={() => setSelectedDifficulty(diff.id)}
                  className={`
                    relative p-6 rounded-2xl border-2 transition-all duration-300
                    ${isSelected 
                      ? `${diff.borderColor} ${diff.glowColor} shadow-2xl scale-105` 
                      : 'border-slate-700 hover:border-slate-600'
                    }
                    bg-slate-800/50 backdrop-blur-sm
                    group
                  `}
                >
                  {/* Gradient Overlay */}
                  {isSelected && (
                    <div className={`absolute inset-0 bg-gradient-to-br ${diff.color} opacity-10 rounded-2xl`}></div>
                  )}
                  
                  <div className="relative z-10">
                    <div className={`
                      w-16 h-16 mx-auto mb-4 rounded-xl flex items-center justify-center
                      bg-gradient-to-br ${diff.color}
                      ${isSelected ? 'scale-110' : 'scale-100 group-hover:scale-105'}
                      transition-transform duration-300
                    `}>
                      <Icon className="w-8 h-8 text-white" strokeWidth={2} />
                    </div>
                    <h3 className="text-2xl font-bold text-white mb-2">{diff.label}</h3>
                    <p className="text-slate-400">{diff.description}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Start Button */}
        <div className="flex justify-center">
          <button
            onClick={() => onStartGame(selectedDifficulty)}
            className="
              group relative px-12 py-5 rounded-2xl font-bold text-xl
              bg-gradient-to-r from-cyan-500 to-blue-600
              hover:from-cyan-400 hover:to-blue-500
              text-white shadow-2xl shadow-cyan-500/50
              hover:shadow-cyan-400/60 hover:scale-105
              transition-all duration-300
              flex items-center gap-3
            "
          >
            <Play className="w-6 h-6 group-hover:translate-x-1 transition-transform" fill="white" />
            Lancer la partie
          </button>
        </div>
      </div>
    </div>
  );
}