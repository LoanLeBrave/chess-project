import { useState } from 'react';
import { WelcomeScreen } from './components/WelcomeScreen';
import { CalibrationScreen } from './components/CalibrationScreen';
import { SafetyScreen } from './components/SafetyScreen';
import { StartScreen } from './components/StartScreen';
import { GameScreen } from './components/GameScreen';

export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced';
export type GameState = 'menu' | 'playing' | 'paused' | 'finished';
export type AppScreen = 'welcome' | 'calibration' | 'safety' | 'difficulty' | 'game';

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
  const [aiHelpEnabled, setAiHelpEnabled] = useState(false);

  const handleWelcomeContinue = () => {
    setCurrentScreen('calibration');
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

  const handleStartGame = (selectedDifficulty: DifficultyLevel, aiHelp: boolean) => {
    setDifficulty(selectedDifficulty);
    setAiHelpEnabled(aiHelp);
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
        <WelcomeScreen onContinue={handleWelcomeContinue} />
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
          aiHelpEnabled={aiHelpEnabled}
        />
      )}
    </div>
  );
}

export default App;