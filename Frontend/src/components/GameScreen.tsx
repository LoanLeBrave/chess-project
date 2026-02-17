import { useState, useEffect } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { ChessBoard } from './ChessBoard';
import { ControlPanel } from './ControlPanel';
import { MoveHistory } from './MoveHistory';
import { RobotStatus } from './RobotStatus';
import { PlayerTurnStatus } from './PlayerTurnStatus';
import { GameOverModal } from './GameOverModal';
import { ScoreSavedNotification } from './ScoreSavedNotification';
import { useChessRobot } from '../hooks/useChessRobot';
import type { DifficultyLevel, GameState, LogEntry } from '../App';

interface GameScreenProps {
  difficulty: DifficultyLevel;
  gameState: GameState;
  setGameState: (state: GameState) => void;
  onReturnToMenu: () => void;
  playerName: string;
}

export interface ChessMove {
  id: string;
  from: string;
  to: string;
  piece: string;
  player: 'human' | 'robot';
  timestamp: Date;
}

export function GameScreen({ difficulty, gameState, setGameState, onReturnToMenu, playerName }: GameScreenProps) {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [moves, setMoves] = useState<ChessMove[]>([]);
  const [showScoreSaved, setShowScoreSaved] = useState(false);
  const [showVision, setShowVision] = useState(false);

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

  const API_BASE = `http://${window.location.hostname}:8000`;

  // Hook personnalise pour gerer la logique d'echecs
  const {
    fen,
    isWhiteTurn,
    isGameOver,
    gameResult,
    robotStatus,
    acplScore,
    visionState,
    onMove,
    getLegalMoves,
    getBestMove,
    resetGame,
    initGame,
  } = useChessRobot(addLog, addMove);

  // Initialiser la partie via l'API au montage
  useEffect(() => {
    initGame(difficulty);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Sauvegarder le score via l'API quand la partie se termine
  const saveScoreToLeaderboard = async (result: 'win' | 'lose' | 'draw' | 'abandoned') => {
    const playerMoves = moves.filter(m => m.player === 'human');
    if (playerMoves.length === 0) return;

    try {
      await fetch(`${API_BASE}/leaderboard/add-game`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          player_name: playerName,
          acpl: acplScore,
          result,
          difficulty,
          moves_played: playerMoves.length,
          game_duration: elapsedTime,
        }),
      });
    } catch {
      // Fallback localStorage si API indisponible
      const leaderboardData = localStorage.getItem('chessLeaderboard');
      const leaderboard = leaderboardData ? JSON.parse(leaderboardData) : [];
      leaderboard.push({
        playerName, acpl: acplScore, result,
        timestamp: new Date().toISOString(),
        moves: playerMoves.length, elapsedTime,
      });
      localStorage.setItem('chessLeaderboard', JSON.stringify(leaderboard));
    }
  };

  useEffect(() => {
    if (isGameOver && gameResult) {
      saveScoreToLeaderboard(gameResult);
    }
  }, [isGameOver, gameResult]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleViewLeaderboard = () => {
    // Cette fonction devra être passée depuis App.tsx pour changer d'écran
    onReturnToMenu();
  };

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

  const handlePause = async () => {
    try {
      const res = await fetch(`${API_BASE}/game/pause`, { method: 'POST' });
      const data = await res.json();
      if (data.paused !== undefined) {
        setGameState(data.paused ? 'paused' : 'playing');
        addLog('info', data.paused ? 'Partie en pause' : 'Partie reprise');
      }
    } catch {
      // Fallback local si API indisponible
      setGameState(gameState === 'playing' ? 'paused' : 'playing');
      addLog('info', gameState === 'playing' ? 'Partie en pause' : 'Partie reprise');
    }
  };

  const handleStop = async () => {
    // Compter uniquement les coups du joueur
    const playerMoves = moves.filter(m => m.player === 'human');

    // Notifier l'API de l'arrêt
    try {
      await fetch(`${API_BASE}/game/stop`, { method: 'POST' });
    } catch {
      // Continue même si l'API est indisponible
    }

    // Sauvegarder le score avant de quitter si le joueur a joué au moins un coup
    if (playerMoves.length > 0 && !isGameOver) {
      saveScoreToLeaderboard('abandoned');
      addLog('warning', 'Partie arrêtée - Score enregistré');
      setShowScoreSaved(true);

      // Fermer la notification après 3 secondes
      setTimeout(() => {
        setShowScoreSaved(false);
        onReturnToMenu();
      }, 3000);
    } else {
      addLog('warning', 'Partie arrêtée par l\'utilisateur');
      onReturnToMenu();
    }
  };

  const handleNewGame = async () => {
    setElapsedTime(0);
    setLogs([]);
    setMoves([]);
    resetGame();
    await initGame(difficulty);
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
              Joueur: <span className="text-cyan-400 font-semibold">{playerName}</span> • 
              Difficulté: <span className="text-cyan-400 font-semibold">
                {difficulty === 'beginner' ? 'Débutant' : difficulty === 'intermediate' ? 'Intermédiaire' : 'Difficile'}
              </span>
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

            {/* Player Turn Status + Vision Toggle */}
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <PlayerTurnStatus isPlayerTurn={isWhiteTurn} />
              </div>
              <button
                onClick={() => setShowVision(!showVision)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  showVision
                    ? 'bg-cyan-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
                title="Afficher/masquer la vision camera"
              >
                {showVision ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                Vision
                {showVision && visionState && (
                  <span className="text-xs opacity-75">({visionState.pieces_count}p)</span>
                )}
              </button>
            </div>
            
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
                showVision={showVision}
                visionBoard={visionState?.board}
                visionConfidence={visionState?.confidence}
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

      {/* Game Over Modal */}
      <GameOverModal
        isVisible={isGameOver}
        result={gameResult || 'draw'}
        acplScore={acplScore}
        totalMoves={moves.length}
        elapsedTime={elapsedTime}
        playerName={playerName}
        onReturnToMenu={handleStop}
        onViewLeaderboard={handleViewLeaderboard}
      />

      {/* Score Saved Notification */}
      <ScoreSavedNotification
        isVisible={showScoreSaved}
        onClose={() => setShowScoreSaved(false)}
        playerName={playerName}
        acplScore={acplScore}
        moves={moves.length}
      />
    </div>
  );
}
