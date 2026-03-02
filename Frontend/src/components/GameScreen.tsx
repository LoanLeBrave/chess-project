import { useState, useEffect, useRef, useCallback } from 'react';
import { Eye, EyeOff, Camera, CheckCircle, AlertTriangle, X, ArrowLeft } from 'lucide-react';
import { ChessBoard } from './ChessBoard';
import { ControlPanel } from './ControlPanel';
import { MoveHistory } from './MoveHistory';
import { RobotStatus } from './RobotStatus';
import { PlayerTurnStatus } from './PlayerTurnStatus';
import { GameOverModal } from './GameOverModal';
import { GameOverModalAbandoned } from './GameOverModalAbandoned';
import { ScoreSavedNotification } from './ScoreSavedNotification';
import { StopConfirmModal } from './StopConfirmModal';
import { PromotionModal } from './PromotionModal';
import { useChessRobot } from '../hooks/useChessRobot';
import type { DifficultyLevel, GameState, LogEntry, GameResults } from '../App';
import { motion } from 'framer-motion';

interface GameScreenProps {
  difficulty: DifficultyLevel;
  gameState: GameState;
  setGameState: (state: GameState) => void;
  onReturnToMenu: () => void;
  onGoToFeedback: (results: GameResults) => void;
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

export function GameScreen({ difficulty, gameState, setGameState, onReturnToMenu, onGoToFeedback, playerName }: GameScreenProps) {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [moves, setMoves] = useState<ChessMove[]>([]);
  const [showScoreSaved, setShowScoreSaved] = useState(false);
  const [showVision, setShowVision] = useState(true);
  const [showStopModal, setShowStopModal] = useState(false);
  const [showScoreModal, setShowScoreModal] = useState(false);
  const [pendingNavigate, setPendingNavigate] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const wasReplacingRef = useRef(false);

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
    visionGameStarted,
    onMove,
    getLegalMoves,
    getBestMove,
    resetGame,
    initGame,
    confirmPlacement,
    illegalMoveAlert,
    dismissIllegalAlert,
    replaceBoard,
    isReplacingBoard,
    isPromotionPending,
    promotionSquare,
    promotionColor,
    confirmPromotion,
    reconnectRobot,
  } = useChessRobot(addLog, addMove);

  // Initialiser la partie via l'API au montage
  useEffect(() => {
    initGame(difficulty);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-dismiss illegal move alert after 8s
  useEffect(() => {
    if (!illegalMoveAlert) return;
    const timer = setTimeout(dismissIllegalAlert, 8000);
    return () => clearTimeout(timer);
  }, [illegalMoveAlert, dismissIllegalAlert]);

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

  // Navigue vers le feedback après remplacement (quand isReplacingBoard passe de true → false)
  useEffect(() => {
    const wasReplacing = wasReplacingRef.current;
    wasReplacingRef.current = isReplacingBoard;
    if (wasReplacing && !isReplacingBoard && pendingNavigate) {
      setPendingNavigate(false);
      
      // Afficher la modal de score puis rediriger vers feedback
      setShowScoreModal(true);
    }
  }, [isReplacingBoard, pendingNavigate]);

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

  // Affiche le modal de confirmation d'arrêt
  const handleStopRequest = useCallback(() => setShowStopModal(true), []);

  // Exécute l'arrêt après confirmation (replace = true si l'utilisateur veut replacer les pièces)
  const executeStop = useCallback(async (replace: boolean) => {
    setShowStopModal(false);

    // Arrêter tous les processus de jeu via l'API
    try {
      await fetch(`${API_BASE}/game/stop`, { method: 'POST' });
    } catch { /* Continue même si l'API est indisponible */ }

    addLog('warning', replace ? 'Partie arrêtée — Replacement en cours...' : 'Partie arrêtée');

    // Sauvegarder le score si le joueur a joué au moins un coup
    const playerMoves = moves.filter(m => m.player === 'human');
    if (playerMoves.length > 0 && !isGameOver) {
      await saveScoreToLeaderboard('abandoned');
    }

    if (replace) {
      // Après le replacement, on affichera la modal de score puis le feedback
      setPendingNavigate(true);
      await replaceBoard();
    } else {
      // Sans replacement, afficher directement la modal de score
      setShowScoreModal(true);
    }
  }, [moves, isGameOver, replaceBoard, addLog]); // eslint-disable-line react-hooks/exhaustive-deps

  // Utilisé par GameOverModal — la partie est déjà terminée, score déjà sauvegardé
  const handleStop = async () => {
    try {
      await fetch(`${API_BASE}/game/stop`, { method: 'POST' });
    } catch { /* Continue */ }
    addLog('info', 'Retour au menu');
    onReturnToMenu();
  };

  const handleNewGame = async () => {
    setElapsedTime(0);
    setLogs([]);
    setMoves([]);
    resetGame();
    await initGame(difficulty);
    addLog('info', 'Nouvelle partie démarrée');
  };

  const handleReplaceBoard = async () => {
    addLog('info', 'Replacement du plateau demandé…');
    await replaceBoard();
  };

  const handleReconnect = async () => {
    setIsReconnecting(true);
    await reconnectRobot();
    setIsReconnecting(false);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="h-screen flex flex-col p-4 overflow-hidden">
      <div className="max-w-[1800px] mx-auto w-full flex-1 flex flex-col">
        {/* Back Button - Top Left */}
        <button
          onClick={handleStopRequest}
          className="
            absolute top-4 left-4 z-10
            w-10 h-10 rounded-lg
            bg-slate-800/50 hover:bg-slate-700/70 backdrop-blur-sm
            border border-slate-700 hover:border-slate-600
            flex items-center justify-center
            text-slate-400 hover:text-white
            transition-all duration-200
            shadow-lg hover:scale-105
          "
          title="Retour"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>

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
              onStop={handleStopRequest}
              onNewGame={handleNewGame}
              onReplaceBoard={handleReplaceBoard}
              onReconnect={handleReconnect}
              isReplacingBoard={isReplacingBoard}
              isReconnecting={isReconnecting}
            />

            {/* Player Turn Status + Vision Controls */}
            <div className="flex items-center gap-2">
              <div className="flex-1">
                <PlayerTurnStatus isPlayerTurn={isWhiteTurn} />
              </div>

              {/* Indicateur partie vision active */}
              {visionGameStarted && (
                <div className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium bg-green-700/50 text-green-300 border border-green-600/50">
                  <CheckCircle className="w-4 h-4" />
                  Vision active
                </div>
              )}

              {/* Toggle vision overlay */}
              <button
                onClick={() => setShowVision(!showVision)}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  showVision
                    ? 'bg-cyan-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
                title="Afficher/masquer la vision camera"
              >
                {showVision ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                {showVision && visionState && (
                  <span className="text-xs opacity-75">{visionState.pieces_count}p</span>
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
        onReturnToMenu={async () => {
          try {
            await fetch(`${API_BASE}/game/stop`, { method: 'POST' });
          } catch { /* Continue */ }
          
          onGoToFeedback({
            result: gameResult || 'draw',
            acplScore,
            totalMoves: moves.length,
            elapsedTime
          });
        }}
        onViewLeaderboard={handleViewLeaderboard}
      />

      {/* Score Modal for Manual Stop */}
      <GameOverModalAbandoned
        isVisible={showScoreModal}
        acplScore={acplScore}
        totalMoves={moves.filter(m => m.player === 'human').length}
        elapsedTime={elapsedTime}
        playerName={playerName}
        onContinue={() => {
          setShowScoreModal(false);
          onGoToFeedback({
            result: 'abandoned',
            acplScore,
            totalMoves: moves.filter(m => m.player === 'human').length,
            elapsedTime
          });
        }}
      />

      {/* Score Saved Notification */}
      <ScoreSavedNotification
        isVisible={showScoreSaved}
        onClose={() => setShowScoreSaved(false)}
        playerName={playerName}
        acplScore={acplScore}
        moves={moves.length}
      />

      {/* Stop Confirmation Modal */}
      <StopConfirmModal
        isVisible={showStopModal}
        onCancel={() => setShowStopModal(false)}
        onConfirm={executeStop}
      />

      {/* Promotion Modal */}
      <PromotionModal
        isVisible={isPromotionPending}
        promotionSquare={promotionSquare || ''}
        promotionColor={promotionColor || 'white'}
        onConfirm={confirmPromotion}
      />

      {/* Illegal Move Alert */}
      {illegalMoveAlert && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.95 }}
          className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50"
        >
          <div className="bg-red-900/95 backdrop-blur-md border-2 border-red-500 rounded-xl px-4 py-3 shadow-2xl shadow-red-500/30 max-w-sm">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-red-100 font-semibold text-sm leading-snug">{illegalMoveAlert.message}</p>
                {illegalMoveAlert.suggestions.length > 0 && (
                  <ul className="mt-1 space-y-0.5">
                    {illegalMoveAlert.suggestions.map((s, i) => (
                      <li key={i} className="text-red-300 text-xs leading-tight">{s}</li>
                    ))}
                  </ul>
                )}
                <p className="text-red-400/70 text-xs mt-1.5">Replacez la pièce et rejouez</p>
              </div>
              <button
                onClick={dismissIllegalAlert}
                className="text-red-400 hover:text-red-200 transition-colors flex-shrink-0"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}