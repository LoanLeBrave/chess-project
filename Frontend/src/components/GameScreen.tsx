import { useState, useEffect } from 'react';
import { ChessBoard } from './ChessBoard';
import { ControlPanel } from './ControlPanel';
import { MoveHistory } from './MoveHistory';
import { RobotStatus } from './RobotStatus';
import { PlayerTurnStatus } from './PlayerTurnStatus';
import { useChessRobot } from '../hooks/useChessRobot';
import type { DifficultyLevel, GameState, LogEntry } from '../App';

interface GameScreenProps {
  difficulty: DifficultyLevel;
  gameState: GameState;
  setGameState: (state: GameState) => void;
  onReturnToMenu: () => void;
  aiHelpEnabled: boolean;
}

export interface ChessMove {
  id: string;
  from: string;
  to: string;
  piece: string;
  player: 'human' | 'robot';
  timestamp: Date;
}

export function GameScreen({ difficulty, gameState, setGameState, onReturnToMenu, aiHelpEnabled }: GameScreenProps) {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [moves, setMoves] = useState<ChessMove[]>([]);

  const addLog = (type: LogEntry['type'], message: string) => {
    const newLog: LogEntry = {
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date(),
      type,
      message
    };
    setLogs(prev => [newLog, ...prev].slice(0, 100));
  };

  const addMove = (move: Omit<ChessMove, 'id' | 'timestamp'>) => {
    const newMove: ChessMove = {
      ...move,
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date()
    };
    setMoves(prev => [...prev, newMove]);
  };

  // Hook personnalisé pour gérer la logique d'échecs
  const {
    fen,
    isWhiteTurn,
    isGameOver,
    robotStatus,
    onMove,
    getLegalMoves,
    getBestMove,
    resetGame
  } = useChessRobot(addLog, addMove);

  // Timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (gameState === 'playing') {
      interval = setInterval(() => {
        setElapsedTime(prev => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [gameState]);

  // Initialize game
  useEffect(() => {
    addLog('info', `Partie initialisée en mode ${difficulty === 'beginner' ? 'Débutant' : difficulty === 'intermediate' ? 'Intermédiaire' : 'Difficile'}`);
    addLog('info', 'Connexion au robot UR7e établie');
    addLog('info', 'Calibration du plateau d\'échecs en cours...');
    
    setTimeout(() => {
      addLog('info', 'Calibration terminée avec succès');
      addLog('info', 'Plateau prêt - Les blancs commencent');
    }, 1500);
  }, []);

  const handlePause = () => {
    setGameState(gameState === 'playing' ? 'paused' : 'playing');
    addLog('info', gameState === 'playing' ? 'Partie en pause' : 'Partie reprise');
  };

  const handleStop = () => {
    addLog('warning', 'Partie arrêtée par l\'utilisateur');
    onReturnToMenu();
  };

  const handleNewGame = () => {
    setElapsedTime(0);
    setLogs([]);
    setMoves([]);
    resetGame();
    addLog('info', 'Nouvelle partie démarrée');
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="h-screen flex flex-col p-4 overflow-hidden">
      <div className="max-w-[1800px] mx-auto w-full flex-1 flex flex-col">
        {/* Header - Compact */}
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">
              Partie en cours
            </h1>
            <p className="text-sm text-slate-400">
              Difficulté: <span className="text-cyan-400 font-semibold">
                {difficulty === 'beginner' ? 'Débutant' : difficulty === 'intermediate' ? 'Intermédiaire' : 'Difficile'}
              </span>
              {aiHelpEnabled && (
                <span className="ml-2 text-xs bg-cyan-500/20 text-cyan-400 px-2 py-1 rounded">
                  Aide IA activée
                </span>
              )}
            </p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-cyan-400 font-mono">
              {formatTime(elapsedTime)}
            </div>
            <div className="text-xs text-slate-500">Temps écoulé</div>
          </div>
        </div>

        {/* Main Grid - Optimized for single screen */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 flex-1 min-h-0">
          {/* Left Column - Controls and Board */}
          <div className="xl:col-span-2 flex flex-col gap-3 min-h-0">
            {/* Control Panel at top - Compact */}
            <ControlPanel
              gameState={gameState}
              onPause={handlePause}
              onStop={handleStop}
              onNewGame={handleNewGame}
            />

            {/* Player Turn Status - Compact */}
            <PlayerTurnStatus isPlayerTurn={isWhiteTurn} />
            
            {/* Chess Board - Flexible size */}
            <div className="flex-1 min-h-0">
              <ChessBoard 
                fen={fen}
                isWhiteTurn={isWhiteTurn}
                robotStatus={robotStatus}
                isGameOver={isGameOver}
                onMove={onMove}
                getLegalMoves={getLegalMoves}
                getBestMove={getBestMove}
                aiHelpEnabled={aiHelpEnabled}
              />
            </div>
          </div>

          {/* Right Column - Info Panels */}
          <div className="flex flex-col gap-3 min-h-0">
            <RobotStatus status={robotStatus} />
            <div className="flex-1 min-h-0">
              <MoveHistory moves={moves} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
