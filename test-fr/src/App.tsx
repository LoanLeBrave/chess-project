import { useState } from 'react';
import { WelcomeScreen } from './components/WelcomeScreen';
import { CalibrationScreen } from './components/CalibrationScreen';
import { SafetyScreen } from './components/SafetyScreen';
import { StartScreen } from './components/StartScreen';
import { GameScreen } from './components/GameScreen';
import { LeaderboardScreen } from './components/LeaderboardScreen';
import { PlacementConfirmationScreen } from './components/PlacementConfirmationScreen';
import { FeedbackScreen } from './components/FeedbackScreen';

export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced';
export type GameState = 'menu' | 'playing' | 'paused' | 'finished';
export type AppScreen = 'welcome' | 'leaderboard' | 'calibration' | 'safety' | 'difficulty' | 'placement' | 'game' | 'feedback';

export interface LogEntry {
  id: string;
  timestamp: Date;
  type: 'info' | 'warning' | 'error' | 'robot' | 'player';
  message: string;
}

export interface GameResults {
  result: 'win' | 'lose' | 'draw' | 'abandoned';
  acplScore: number;
  totalMoves: number;
  elapsedTime: number;
}

function App() {
  const [currentScreen, setCurrentScreen] = useState<AppScreen>('welcome');
  const [gameState, setGameState] = useState<GameState>('menu');
  const [difficulty, setDifficulty] = useState<DifficultyLevel>('beginner');
  const [playerName, setPlayerName] = useState('');
  const [gameResults, setGameResults] = useState<GameResults | null>(null);

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
    setCurrentScreen('placement');
  };

  const handleStartBack = () => {
    setCurrentScreen('safety');
  };

  const handlePlacementConfirm = () => {
    setGameState('playing');
    setCurrentScreen('game');
  };

  const handlePlacementBack = () => {
    setCurrentScreen('difficulty');
  };

  const handleReturnToMenu = () => {
    setGameState('menu');
    setCurrentScreen('welcome');
  };

  const handleGoToFeedback = (results: GameResults) => {
    setGameResults(results);
    setCurrentScreen('feedback');
  };

  const handleFeedbackComplete = () => {
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
      {currentScreen === 'placement' && (
        <PlacementConfirmationScreen
          onConfirm={handlePlacementConfirm}
          onBack={handlePlacementBack}
        />
      )}
      {currentScreen === 'game' && (
        <GameScreen 
          difficulty={difficulty}
          gameState={gameState}
          setGameState={setGameState}
          onReturnToMenu={handleReturnToMenu}
          onGoToFeedback={handleGoToFeedback}
          playerName={playerName}
        />
      )}
      {currentScreen === 'feedback' && gameResults && (
        <FeedbackScreen
          onReturnToMenu={handleFeedbackComplete}
          playerName={playerName}
          difficulty={difficulty}
          result={gameResults.result}
          acplScore={gameResults.acplScore}
        />
      )}
    </div>
  );
}

export default App;