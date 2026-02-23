import { useState } from 'react';
import { WelcomeScreen } from './components/WelcomeScreen';
import { CalibrationScreen } from './components/CalibrationScreen';
import { SafetyScreen } from './components/SafetyScreen';
import { StartScreen } from './components/StartScreen';
import { GameScreen } from './components/GameScreen';
import { LeaderboardScreen } from './components/LeaderboardScreen';

export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced';
export type GameState = 'menu' | 'playing' | 'paused' | 'finished';
export type AppScreen = 'welcome' | 'leaderboard' | 'calibration' | 'safety' | 'difficulty' | 'game';

export interface LogEntry {
  id: string;
  timestamp: Date;
  type: 'info' | 'warning' | 'error' | 'robot' | 'player';
  message: string;
}

function App() {
  const [currentScreen, setCurrentScreen] = useState<AppScreen>('welcome');
  const [gameState, setGameState] = useState<GameState>('menu');
  const [difficulty, setDifficulty] = useState<DifficultyLevel>('beginner');
  const [playerName, setPlayerName] = useState('');

  const handleWelcomeContinue = () => {
    setCurrentScreen('calibration');
  };

  const handleViewLeaderboard = () => {
    setCurrentScreen('leaderboard');
  };

  const handleLeaderboardBack = () => {
    setCurrentScreen('welcome');
  };

  const handleCalibrationComplete = () => {
    setCurrentScreen('safety');
  };

  const handleCalibrationBack = () => {
    setCurrentScreen('welcome');
  };


  const handleSafetyContinue = () => {
    setCurrentScreen('difficulty');
  };

  const handleSafetyBack = () => {
    setCurrentScreen('calibration');
  };

  const handleStartGame = (selectedDifficulty: DifficultyLevel, name: string) => {
    setDifficulty(selectedDifficulty);
    setPlayerName(name);
    setGameState('playing');
    setCurrentScreen('game');
  };

  const handleStartBack = () => {
    setCurrentScreen('safety');
  };

  const handleReturnToMenu = () => {
    setGameState('menu');
    setCurrentScreen('welcome');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {currentScreen === 'welcome' && (
        <WelcomeScreen 
          onContinue={handleWelcomeContinue}
          onViewLeaderboard={handleViewLeaderboard}
        />
      )}
      {currentScreen === 'leaderboard' && (
        <LeaderboardScreen onBack={handleLeaderboardBack} />
      )}
      {currentScreen === 'calibration' && (
        <CalibrationScreen 
          onCalibrationComplete={handleCalibrationComplete}
          onBack={handleCalibrationBack}
        />
      )}
      {currentScreen === 'safety' && (
        <SafetyScreen 
          onContinue={handleSafetyContinue}
          onBack={handleSafetyBack}
        />
      )}
      {currentScreen === 'difficulty' && (
        <StartScreen 
          onStartGame={handleStartGame}
          onBack={handleStartBack}
        />
      )}
      {currentScreen === 'game' && (
        <GameScreen 
          difficulty={difficulty}
          gameState={gameState}
          setGameState={setGameState}
          onReturnToMenu={handleReturnToMenu}
          playerName={playerName}
        />
      )}
    </div>
  );
}

export default App;