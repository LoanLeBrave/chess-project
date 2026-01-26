import { useState } from 'react';
import { StartScreen } from './components/StartScreen';
import { GameScreen } from './components/GameScreen';

export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced';
export type GameState = 'menu' | 'playing' | 'paused' | 'finished';

export interface LogEntry {
  id: string;
  timestamp: Date;
  type: 'info' | 'warning' | 'error' | 'robot' | 'player';
  message: string;
}

function App() {
  const [gameState, setGameState] = useState<GameState>('menu');
  const [difficulty, setDifficulty] = useState<DifficultyLevel>('beginner');

  const handleStartGame = (selectedDifficulty: DifficultyLevel) => {
    setDifficulty(selectedDifficulty);
    setGameState('playing');
  };

  const handleReturnToMenu = () => {
    setGameState('menu');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {gameState === 'menu' ? (
        <StartScreen onStartGame={handleStartGame} />
      ) : (
        <GameScreen 
          difficulty={difficulty}
          gameState={gameState}
          setGameState={setGameState}
          onReturnToMenu={handleReturnToMenu}
        />
      )}
    </div>
  );
}

export default App;