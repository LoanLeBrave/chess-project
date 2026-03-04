import { useState, useEffect, useRef, useCallback } from 'react';
import { Eye, EyeOff, Camera, CheckCircle, AlertTriangle, X, ArrowLeft, RotateCcw, Pencil, Pause } from 'lucide-react';
import { ChessBoard } from './ChessBoard';
import { ControlPanel } from './ControlPanel';
import { MoveHistory } from './MoveHistory';
import { RobotStatus } from './RobotStatus';
import { PlayerTurnStatus } from './PlayerTurnStatus';
import { GameOverModal } from './GameOverModal';
import { GameOverModalAbandoned } from './GameOverModalAbandoned';
import { ScoreSavedNotification } from './ScoreSavedNotification';
import { StopConfirmModal } from './StopConfirmModal';
import { RestartConfirmModal } from './RestartConfirmModal';
import { PromotionModal } from './PromotionModal';
import { CheckmateWarning } from './CheckmateWarning';
import { useChessRobot } from '../hooks/useChessRobot';
import type { DifficultyLevel, GameState, LogEntry, GameResults } from '../App';
import { motion } from 'motion/react';

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
  
  // Resume alert state
  const [showResumeAlert, setShowResumeAlert] = useState(false);
  
  // Restart modal state
  const [showRestartModal, setShowRestartModal] = useState(false);
  
  // Checkmate warning states
  const [showCheckmateWarning, setShowCheckmateWarning] = useState(false);
  const [checkmateWarningType, setCheckmateWarningType] = useState<'danger' | 'opportunity'>('danger');

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
    isPromotionPending,
    promotionSquare,
    promotionColor,
    confirmPromotion,
    reconnectRobot,
    resumeConfirmation,
    confirmResume,
    isCorrectionMode,
    undoLastMove,
    enterCorrectionMode,
    exitCorrectionMode,
    correctMove,
  } = useChessRobot(addLog, addMove);

  // État pour le replacement du plateau
  const [isReplacingBoard, setIsReplacingBoard] = useState(false);

  // Fonction pour replacer le plateau
  const replaceBoard = async () => {
    setIsReplacingBoard(true);
    try {
      const res = await fetch(`${API_BASE}/board/replace`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        addLog('info', 'Plateau replacé avec succès');
      } else {
        addLog('error', data.error || 'Erreur lors du replacement');
      }
    } catch (err) {
      addLog('error', `Erreur replacement: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsReplacingBoard(false);
    }
  };

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

  // Check for forced checkmate (call API with FEN to get Stockfish analysis)
  useEffect(() => {
    if (isGameOver || moves.length === 0) return;

    const checkForForcedCheckmate = async () => {
      try {
        const res = await fetch(`${API_BASE}/game/analyze-position`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ fen })
        });
        const data = await res.json();

        // data.forced_mate could be: null, positive number (white wins in N moves), negative number (black wins in N moves)
        if (data.forced_mate !== null && data.forced_mate !== undefined) {
          const movesUntilMate = Math.abs(data.forced_mate);
          
          // Only show warning if mate is within 5 moves
          if (movesUntilMate <= 5 && movesUntilMate > 0) {
            if (data.forced_mate > 0) {
              // White (player) has forced mate
              setCheckmateWarningType('opportunity');
              setShowCheckmateWarning(true);
              addLog('info', `Mat forcé en ${movesUntilMate} coup(s) !`);
            } else {
              // Black (robot) has forced mate
              setCheckmateWarningType('danger');
              setShowCheckmateWarning(true);
              addLog('warning', `Attention ! Mat imminent en ${movesUntilMate} coup(s)`);
            }
          }
        }
      } catch {
        // API not available or error - silently ignore
      }
    };

    // Check after each move with a small delay
    const timer = setTimeout(checkForForcedCheckmate, 1000);
    return () => clearTimeout(timer);
  }, [fen, moves.length, isGameOver, addLog]); // eslint-disable-line react-hooks/exhaustive-deps

  // Sauvegarder le score via l'API quand la partie se termine
  const saveScoreToLeaderboard = async (result: 'win' | 'lose' | 'draw' | 'abandoned') => {
    const playerMoves = moves.filter(m => m.player === 'human');
    if (playerMoves.length === 0) return;

    try {
      const res = await fetch(`${API_BASE}/leaderboard/add-game`, {
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
      if (res.ok) {
        setShowScoreSaved(true);
        setTimeout(() => setShowScoreSaved(false), 4000);
      }
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
    // Arrêter le timer si en pause, si modal stop ouvert, si partie terminée, ou si gameState !== 'playing'
    if (gameState === 'playing' && !showStopModal && !isGameOver) {
      interval = setInterval(() => {
        setElapsedTime(prev => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [gameState, showStopModal, isGameOver]);

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
    const wasPaused = gameState === 'paused';
    
    // Si on veut reprendre depuis pause, afficher d'abord la confirmation
    if (wasPaused) {
      setShowResumeAlert(true);
      return;
    }
    
    // Si on met en pause, pas besoin de confirmation
    try {
      const res = await fetch(`${API_BASE}/game/pause`, { method: 'POST' });
      const data = await res.json();
      if (data.paused !== undefined) {
        setGameState(data.paused ? 'paused' : 'playing');
        addLog('info', data.paused ? 'Partie en pause' : 'Partie reprise');
      }
    } catch {
      // Fallback local si API indisponible
      setGameState('paused');
      addLog('info', 'Partie en pause');
    }
  };

  // Confirmer la reprise après vérification des pièces

  const handleManualResume = async () => {
    setShowResumeAlert(false);
    try {
      const res = await fetch(`${API_BASE}/game/pause`, { method: 'POST' });
      const data = await res.json();
      if (data.paused !== undefined) {
        setGameState(data.paused ? 'paused' : 'playing');
        addLog('info', 'Partie reprise');
      }
    } catch {
      setGameState('playing');
      addLog('info', 'Partie reprise');
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
    setShowRestartModal(true);
  };

  const executeRestart = async (replace: boolean) => {
    setShowRestartModal(false);
    
    // Reset UI state immediately
    setElapsedTime(0);
    setLogs([]);
    setMoves([]);

    if (replace) {
      addLog('info', 'Replacement du plateau avant la nouvelle partie…');
      await replaceBoard();
    }
    
    resetGame();
    await initGame(difficulty);
    addLog('info', 'Nouvelle partie démarrée');
  };

  const handleReconnect = async () => {
    setIsReconnecting(true);
    await reconnectRobot();
    setIsReconnecting(false);
  };

  const handleUndo = async () => {
    const count = await undoLastMove();
    if (count > 0) {
      setMoves(prev => prev.slice(0, Math.max(0, prev.length - count)));
    }
  };

  const handleEnterCorrection = async () => {
    const count = await enterCorrectionMode();
    if (count > 0) {
      setMoves(prev => prev.slice(0, Math.max(0, prev.length - count)));
      addLog('info', 'Mode correction — cliquez la case de départ puis la case d\'arrivée correctes sur le plateau');
    }
  };

  const handleCorrectionMove = useCallback(async (from: string, to: string): Promise<boolean> => {
    return await correctMove(from, to);
  }, [correctMove]);

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
              onReconnect={handleReconnect}
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

              {/* Boutons Annuler / Corriger */}
              {!isGameOver && moves.length > 0 && !isReplacingBoard && (
                <>
                  <button
                    onClick={handleUndo}
                    disabled={robotStatus !== 'idle' || isCorrectionMode}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium bg-slate-700 hover:bg-slate-600 text-slate-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    title="Annuler le dernier coup"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Annuler
                  </button>
                  <button
                    onClick={isCorrectionMode ? exitCorrectionMode : handleEnterCorrection}
                    disabled={!isCorrectionMode && robotStatus !== 'idle'}
                    className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isCorrectionMode
                        ? 'bg-amber-600 hover:bg-amber-500 text-white'
                        : 'bg-slate-700 hover:bg-slate-600 text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed'
                    }`}
                    title={isCorrectionMode ? 'Annuler la correction' : 'Corriger un coup mal détecté par la caméra'}
                  >
                    <Pencil className="w-4 h-4" />
                    {isCorrectionMode ? 'Annuler correction' : 'Corriger'}
                  </button>
                </>
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
            
            {/* Chess Board - taille fixe, centrée */}
            <div className="flex-1 min-h-0 flex items-start justify-center overflow-auto pt-1">
              <ChessBoard
                fen={fen}
                isWhiteTurn={isWhiteTurn}
                robotStatus={robotStatus}
                isGameOver={isGameOver}
                onMove={isCorrectionMode ? handleCorrectionMove : onMove}
                getLegalMoves={getLegalMoves}
                getBestMove={getBestMove}
                showVision={showVision && !isCorrectionMode}
                visionBoard={visionState?.board}
                visionConfidence={visionState?.confidence}
                isCorrectionMode={isCorrectionMode}
                cemeteryBoard={visionState?.cemetery_board}
                piecesEliminees={visionState?.pieces_eliminees}
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

      {/* Restart Confirmation Modal */}
      <RestartConfirmModal
        isVisible={showRestartModal}
        onCancel={() => setShowRestartModal(false)}
        onConfirm={executeRestart}
      />

      {/* Promotion Modal */}
      <PromotionModal
        isVisible={isPromotionPending}
        promotionSquare={promotionSquare || ''}
        promotionColor={promotionColor || 'white'}
        onConfirm={confirmPromotion}
      />

      {/* Resume Confirmation Alert */}
      {resumeConfirmation && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 animate-in slide-in-from-bottom-4">
          <div className="bg-amber-900 border border-amber-500 rounded-xl px-5 py-4 shadow-2xl max-w-md w-full">
            <div className="flex items-start gap-3 mb-3">
              <AlertTriangle className="w-6 h-6 text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-amber-100 font-semibold text-sm">Partie reprise — pince relâchée</p>
                <p className="text-amber-200 text-sm mt-1">
                  Le <span className="font-bold text-amber-300">{resumeConfirmation.pieceName}</span> devait
                  aller en <span className="font-bold text-amber-400">{resumeConfirmation.toSq}</span>.
                  Replacez-le manuellement sur cette case.
                </p>
              </div>
            </div>
            <button
              onClick={confirmResume}
              className="w-full px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-medium text-sm transition-colors"
            >
              Pièce replacée — Continuer la partie
            </button>
          </div>
        </div>
      )}

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

      {/* Checkmate Warning */}
      <CheckmateWarning
        isVisible={showCheckmateWarning}
        type={checkmateWarningType}
        onClose={() => setShowCheckmateWarning(false)}
      />

      {/* Resume Game Confirmation - Must validate pieces placement */}
      {showResumeAlert && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
        >
          <motion.div
            initial={{ y: 20 }}
            animate={{ y: 0 }}
            className="bg-gradient-to-br from-slate-800 via-slate-800 to-slate-900 backdrop-blur-xl border-2 border-cyan-400 rounded-2xl p-8 shadow-2xl shadow-cyan-500/50 max-w-xl w-full"
          >
            <div className="flex items-start gap-5 mb-6">
              <div className="flex-shrink-0">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/50">
                  <Pause className="w-8 h-8 text-white" strokeWidth={2.5} fill="currentColor" />
                </div>
              </div>
              <div className="flex-1">
                <h3 className="text-white font-bold text-2xl mb-2">
                  Partie en pause
                </h3>
                <p className="text-cyan-50 text-base leading-relaxed">
                  Avant de reprendre la partie, veuillez vérifier que <span className="font-bold text-cyan-300">toutes les pièces sont correctement placées</span> sur l'échiquier.
                </p>
              </div>
            </div>

            <div className="bg-cyan-500/10 rounded-xl p-4 mb-6 border border-cyan-400/40">
              <div className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1 space-y-2 text-sm text-slate-200">
                  <p>• Le robot a relâché la pince et est en position de repos</p>
                  <p>• Vérifiez que chaque pièce est bien centrée sur sa case</p>
                  <p>• Assurez-vous qu'aucune pièce n'a été déplacée par erreur</p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowResumeAlert(false)}
                className="flex-1 px-5 py-3 rounded-xl bg-slate-700 hover:bg-slate-600 text-slate-200 hover:text-white font-semibold text-base transition-all duration-200 border border-slate-600 hover:border-slate-500"
              >
                Annuler
              </button>
              <button
                onClick={handleManualResume}
                className="flex-1 px-5 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white font-bold text-base transition-all duration-200 shadow-lg shadow-cyan-500/40 hover:shadow-cyan-500/60 hover:scale-[1.02]"
              >
                ✓ Tout est OK, reprendre
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}

      {/* Replacement Loading Modal */}
      {isReplacingBoard && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
        >
          <motion.div
            initial={{ scale: 0.9, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            className="bg-slate-900/95 border-2 border-cyan-500/50 rounded-2xl p-8 shadow-2xl shadow-cyan-500/40 max-w-md w-full mx-4"
          >
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/40">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                >
                  <RotateCcw className="w-10 h-10 text-white" />
                </motion.div>
              </div>
              <h3 className="text-white font-bold text-2xl mb-2">
                Replacement en cours
              </h3>
              <p className="text-cyan-100 text-base leading-relaxed mb-4">
                Le robot UR7e replace toutes les pièces en position initiale...
              </p>
              <div className="flex items-center justify-center gap-2">
                <motion.div
                  className="w-2 h-2 rounded-full bg-cyan-400"
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ duration: 1.5, repeat: Infinity, delay: 0 }}
                />
                <motion.div
                  className="w-2 h-2 rounded-full bg-cyan-400"
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ duration: 1.5, repeat: Infinity, delay: 0.2 }}
                />
                <motion.div
                  className="w-2 h-2 rounded-full bg-cyan-400"
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ duration: 1.5, repeat: Infinity, delay: 0.4 }}
                />
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </div>
  );
}