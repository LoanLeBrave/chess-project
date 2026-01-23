// components/GameScreen.tsx
import { useState, useEffect } from 'react';
import { ChessBoard } from './ChessBoard';
import { ControlPanel } from './ControlPanel';
import { MoveHistory } from './MoveHistory';
import { RobotStatus } from './RobotStatus';
import { PlayerTurnStatus } from './PlayerTurnStatus';
import { useChessRobot } from '../hooks/useChessRobot';
import type { DifficultyLevel, GameState } from '../App';

interface GameScreenProps {
  difficulty: DifficultyLevel;
  gameState: GameState;
  setGameState: (state: GameState) => void;
  onReturnToMenu: () => void;
}

export function GameScreen({ difficulty, gameState, setGameState, onReturnToMenu }: GameScreenProps) {
  const [elapsedTime, setElapsedTime] = useState(0);
  
  const {
    connected,
    robotConnected,
    status,
    fen,
    isWhiteTurn,
    isGameOver,
    gameResult,
    logs,
    moves,
    newGame,
    playHumanMove,
    playRobotMove,
    getLegalMoves,
    addLog
  } = useChessRobot();

  // Timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (gameState === 'playing' && !isGameOver) {
      interval = setInterval(() => {
        setElapsedTime(prev => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [gameState, isGameOver]);

  // Initialiser la partie au montage
  useEffect(() => {
    if (connected) {
      newGame(difficulty);
    }
  }, [connected, difficulty]);

  // Déclencher le coup du robot quand c'est son tour
  useEffect(() => {
    if (connected && !isWhiteTurn && status === 'idle' && gameState === 'playing' && !isGameOver) {
      // Petit délai avant que le robot joue
      const timeout = setTimeout(() => {
        playRobotMove();
      }, 500);
      
      return () => clearTimeout(timeout);
    }
  }, [connected, isWhiteTurn, status, gameState, isGameOver, playRobotMove]);

  // Gérer le coup du joueur
  const handlePlayerMove = async (from: string, to: string): Promise<boolean> => {
    if (gameState !== 'playing') return false;
    
    const success = await playHumanMove(from, to);
    return success;
  };

  const handlePause = () => {
    setGameState(gameState === 'playing' ? 'paused' : 'playing');
    addLog('info', gameState === 'playing' ? 'Partie en pause' : 'Partie reprise');
  };

  const handleStop = () => {
    addLog('warning', 'Partie arrêtée');
    onReturnToMenu();
  };

  const handleNewGame = () => {
    setElapsedTime(0);
    newGame(difficulty);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Convertir le status pour le composant RobotStatus
  const robotStatusForComponent = status === 'disconnected' ? 'error' : status;

  // Convertir les moves pour MoveHistory
  const movesForHistory = moves.map(m => ({
    id: m.id,
    from: m.from,
    to: m.to,
    piece: m.san.charAt(0).toUpperCase() === m.san.charAt(0) ? m.san.charAt(0) : '♙',
    player: m.player,
    timestamp: m.timestamp
  }));

  return (
    <div className="h-screen flex flex-col p-4 overflow-hidden">
      <div className="max-w-[1800px] mx-auto w-full flex-1 flex flex-col">
        {/* Header */}
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              Partie en cours
              {/* Indicateur de connexion */}
              <span className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'} animate-pulse`}></span>
            </h1>
            <p className="text-sm text-slate-400">
              Difficulté: <span className="text-cyan-400 font-semibold">
                {difficulty === 'beginner' ? 'Débutant' : difficulty === 'intermediate' ? 'Intermédiaire' : 'Difficile'}
              </span>
              {!robotConnected && connected && (
                <span className="text-yellow-400 ml-2">(Mode simulation)</span>
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

        {/* Résultat de la partie */}
        {isGameOver && gameResult && (
          <div className="mb-3 bg-gradient-to-r from-yellow-500/20 to-orange-500/20 border border-yellow-500/50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-yellow-400">
              🏆 {gameResult}
            </div>
          </div>
        )}

        {/* Main Grid */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 flex-1 min-h-0">
          {/* Left Column */}
          <div className="xl:col-span-2 flex flex-col gap-3 min-h-0">
            <ControlPanel
              gameState={gameState}
              onPause={handlePause}
              onStop={handleStop}
              onNewGame={handleNewGame}
            />

            <PlayerTurnStatus isPlayerTurn={isWhiteTurn && status === 'idle'} />
            
            <div className="flex-1 min-h-0">
              <ChessBoard 
                fen={fen}
                isWhiteTurn={isWhiteTurn}
                robotStatus={status}
                isGameOver={isGameOver}
                onMove={handlePlayerMove}
                getLegalMoves={getLegalMoves}
              />
            </div>
          </div>

          {/* Right Column */}
          <div className="flex flex-col gap-3 min-h-0">
            <RobotStatus status={robotStatusForComponent} />
            
            {/* Logs en temps réel */}
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700 max-h-48 overflow-hidden">
              <h3 className="text-white font-semibold mb-2 flex items-center gap-2 text-sm">
                <div className="w-1 h-4 bg-cyan-400 rounded-full"></div>
                Logs
              </h3>
              <div className="space-y-1 overflow-y-auto max-h-32 text-xs">
                {logs.slice(0, 10).map(log => (
                  <div 
                    key={log.id}
                    className={`
                      px-2 py-1 rounded
                      ${log.type === 'error' ? 'bg-red-900/30 text-red-400' : ''}
                      ${log.type === 'warning' ? 'bg-yellow-900/30 text-yellow-400' : ''}
                      ${log.type === 'robot' ? 'bg-cyan-900/30 text-cyan-400' : ''}
                      ${log.type === 'player' ? 'bg-blue-900/30 text-blue-400' : ''}
                      ${log.type === 'info' ? 'bg-slate-700/30 text-slate-400' : ''}
                    `}
                  >
                    <span className="font-mono text-slate-500">
                      {log.timestamp.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                    {' '}{log.message}
                  </div>
                ))}
              </div>
            </div>
            
            <div className="flex-1 min-h-0">
              <MoveHistory moves={movesForHistory} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
