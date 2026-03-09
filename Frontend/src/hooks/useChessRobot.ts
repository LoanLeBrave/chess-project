import { useState, useCallback, useEffect, useRef } from 'react';
import { Chess } from 'chess.js';

export type RobotStatus = 'idle' | 'thinking' | 'moving' | 'error' | 'disconnected' | 'replacing';

export interface MoveEvaluation {
  move: string;
  centipawnLoss: number;
}

export interface PieceEliminee {
  piece: string;        // 'P', 'N', 'B', 'R', 'Q', 'K'
  color: 'white' | 'black';
  case_cimetiere: string; // ex: "a0", "b9"
  case_origine: string;
  index: number;
}

export interface PiecesEliminees {
  blanches: PieceEliminee[];
  noires: PieceEliminee[];
}

export interface VisionState {
  board: { [square: string]: string };
  confidence: { [square: string]: number };
  pieces_count: number;
  game_started: boolean;
  reference_set: boolean;
  /** Pièces détectées physiquement dans la zone cimetière {"a0":"WP", "a9":"BP"...} */
  cemetery_board: { [square: string]: string };
  /** Pièces éliminées telles que tracées par le robot (vue Stockfish) */
  pieces_eliminees: PiecesEliminees;
}

export interface IllegalMoveAlert {
  message: string;
  suggestions: string[];
  timestamp: number;
}

export interface ResumeConfirmation {
  pieceName: string;
  fromSq: string;
  toSq: string;
  player: 'human' | 'robot';
}

export interface UseChessRobotReturn {
  fen: string;
  isWhiteTurn: boolean;
  isGameOver: boolean;
  gameResult: 'win' | 'lose' | 'draw' | null;
  robotStatus: RobotStatus;
  acplScore: number;
  moveEvaluations: MoveEvaluation[];
  visionState: VisionState | null;
  visionGameStarted: boolean;
  illegalMoveAlert: IllegalMoveAlert | null;
  isReplacingBoard: boolean;
  isPromotionPending: boolean;
  promotionSquare: string | null;
  promotionColor: 'white' | 'black' | null;
  setRobotStatus: (status: RobotStatus) => void;
  onMove: (from: string, to: string) => Promise<boolean>;
  getLegalMoves: (square: string) => Promise<string[]>;
  getBestMove: () => Promise<{ from: string; to: string } | null>;
  resetGame: () => void;
  initGame: (difficulty: string) => Promise<void>;
  confirmPlacement: (useCamera: boolean) => Promise<boolean>;
  dismissIllegalAlert: () => void;
  replaceBoard: () => Promise<boolean>;
  confirmPromotion: (from_sq: string) => Promise<boolean>;
  reconnectRobot: () => Promise<boolean>;
  resumeConfirmation: ResumeConfirmation | null;
  confirmResume: () => Promise<boolean>;
  isCorrectionMode: boolean;
  undoLastMove: () => Promise<number>;
  enterCorrectionMode: () => Promise<number>;
  exitCorrectionMode: () => void;
  correctMove: (from: string, to: string) => Promise<boolean>;
  isDemoMode: boolean;
  demoCycle: number;
  demoMoveCount: number;
  demoMovesPerCycle: number;
  startDemo: (movesPerCycle?: number, delayBetweenMoves?: number) => Promise<boolean>;
  stopDemo: () => Promise<boolean>;
  gotoTurn: (turn: number) => Promise<boolean>;
}

const API_BASE = `${window.location.protocol}//${window.location.hostname}:8000`;
const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:8000/ws`;

const INITIAL_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

function getPieceName(piece: string): string {
  const names: { [key: string]: string } = {
    'K': 'Roi', 'Q': 'Dame', 'R': 'Tour', 'B': 'Fou', 'N': 'Cavalier', 'P': 'Pion',
    'k': 'Roi', 'q': 'Dame', 'r': 'Tour', 'b': 'Fou', 'n': 'Cavalier', 'p': 'Pion'
  };
  return names[piece] || 'Piece';
}

function fenToBoard(fen: string): { [key: string]: string } {
  const board: { [key: string]: string } = {};
  const [position] = fen.split(' ');
  const rows = position.split('/');
  const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];

  rows.forEach((row, rowIndex) => {
    const rank = 8 - rowIndex;
    let fileIndex = 0;
    for (const char of row) {
      if (isNaN(parseInt(char))) {
        board[`${files[fileIndex]}${rank}`] = char;
        fileIndex++;
      } else {
        fileIndex += parseInt(char);
      }
    }
  });
  return board;
}

/**
 * Hook pour gerer la logique du jeu d'echecs via l'API backend
 */
export function useChessRobot(
  addLog: (type: 'info' | 'warning' | 'error' | 'robot' | 'player', message: string) => void,
  onMoveComplete: (move: { from: string; to: string; piece: string; player: 'human' | 'robot' }) => void,
  onGotoTurnComplete?: (turn: number, fen: string) => void
): UseChessRobotReturn {
  const [fen, setFen] = useState(INITIAL_FEN);
  const fenRef = useRef(INITIAL_FEN);
  // Garder fenRef synchronisé à chaque changement de FEN
  useEffect(() => { fenRef.current = fen; }, [fen]);
  const [isWhiteTurn, setIsWhiteTurn] = useState(true);
  const [isGameOver, setIsGameOver] = useState(false);
  const [gameResult, setGameResult] = useState<'win' | 'lose' | 'draw' | null>(null);
  const [robotStatus, setRobotStatus] = useState<RobotStatus>('disconnected');
  const [moveEvaluations, setMoveEvaluations] = useState<MoveEvaluation[]>([]);
  const [acplScore, setAcplScore] = useState(0);
  const [visionState, setVisionState] = useState<VisionState | null>(null);
  const [visionGameStarted, setVisionGameStarted] = useState(false);
  const [illegalMoveAlert, setIllegalMoveAlert] = useState<IllegalMoveAlert | null>(null);
  const [isReplacingBoard, setIsReplacingBoard] = useState(false);
  
  // Promotion states
  const [isPromotionPending, setIsPromotionPending] = useState(false);
  const [promotionSquare, setPromotionSquare] = useState<string | null>(null);
  const [promotionColor, setPromotionColor] = useState<'white' | 'black' | null>(null);
  const [resumeConfirmation, setResumeConfirmation] = useState<ResumeConfirmation | null>(null);
  const [isCorrectionMode, setIsCorrectionMode] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [demoCycle, setDemoCycle] = useState(0);
  const [demoMoveCount, setDemoMoveCount] = useState(0);
  const [demoMovesPerCycle, setDemoMovesPerCycle] = useState(10);

  const wsRef = useRef<WebSocket | null>(null);
  const addLogRef = useRef(addLog);
  const onMoveCompleteRef = useRef(onMoveComplete);
  const onGotoTurnCompleteRef = useRef(onGotoTurnComplete);
  const isDemoModeRef = useRef(false);

  // Mettre à jour les refs quand les callbacks changent
  useEffect(() => {
    addLogRef.current = addLog;
  }, [addLog]);

  useEffect(() => {
    onMoveCompleteRef.current = onMoveComplete;
  }, [onMoveComplete]);

  useEffect(() => {
    onGotoTurnCompleteRef.current = onGotoTurnComplete;
  }, [onGotoTurnComplete]);

  // --- WebSocket ---
  useEffect(() => {
    let reconnectTimer: NodeJS.Timeout;

    const connect = () => {
      console.log('Tentative de connexion WebSocket...');
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        setRobotStatus('idle');
        addLogRef.current('info', 'Connexion WebSocket etablie');
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === 'status') {
            const statusMap: { [key: string]: RobotStatus } = {
              'idle': 'idle', 'thinking': 'thinking', 'moving': 'moving',
              'error': 'error', 'paused': 'idle', 'replacing': 'replacing'
            };
            setRobotStatus(statusMap[msg.status] || 'idle');
            
            if (msg.status === 'replacing') {
              setIsReplacingBoard(true);
            } else {
              setIsReplacingBoard(false);
            }
          }

          if (msg.type === 'move') {
            setFen(msg.fen);
            setIsWhiteTurn(msg.fen.split(' ')[1] === 'w');

            if (msg.player === 'robot') {
              onMoveCompleteRef.current({
                from: msg.from,
                to: msg.to,
                piece: msg.san ? msg.san[0] : 'Piece',
                player: 'robot'
              });
              addLogRef.current('robot', `Robot joue: ${msg.san || msg.from + ' -> ' + msg.to}`);
              setRobotStatus('idle');
              // Mise à jour ACPL via le CPL calculé par le backend (couvre mode manuel ET vision)
              if (typeof msg.cpl === 'number') {
                setMoveEvaluations(prev => {
                  const updated = [...prev, { move: `${msg.from}-${msg.to}`, centipawnLoss: msg.cpl }];
                  const total = updated.reduce((sum, e) => sum + e.centipawnLoss, 0);
                  setAcplScore(Math.round(total / updated.length));
                  return updated;
                });
              }
            } else if (msg.player === 'human') {
              // Coup humain detecte par la vision camera
              onMoveCompleteRef.current({
                from: msg.from,
                to: msg.to,
                piece: msg.san ? msg.san[0] : 'Piece',
                player: 'human'
              });
              addLogRef.current('player', `Coup detecte: ${msg.san || msg.from + ' -> ' + msg.to}`);
              setRobotStatus('thinking');
            }
          }

          if (msg.type === 'game_over' && !isDemoModeRef.current) {
            setIsGameOver(true);
            const result = msg.result as string;
            if (result.includes('Blancs')) {
              setGameResult('win');
            } else if (result.includes('Noirs')) {
              setGameResult('lose');
            } else {
              setGameResult('draw');
            }
            addLogRef.current('info', result);
          }

          if (msg.type === 'log') {
            addLogRef.current(msg.logType || 'info', msg.message);
          }

          if (msg.type === 'connected') {
            setFen(msg.fen);
            setIsWhiteTurn(msg.fen.split(' ')[1] === 'w');
            setRobotStatus(msg.robot_connected ? 'idle' : 'disconnected');
          }

          if (msg.type === 'vision_state') {
            setVisionState({
              board: msg.board || {},
              confidence: msg.confidence || {},
              pieces_count: msg.pieces_count || 0,
              game_started: msg.game_started || false,
              reference_set: msg.reference_set || false,
              cemetery_board: msg.cemetery_board || {},
              pieces_eliminees: msg.pieces_eliminees || { blanches: [], noires: [] },
            });
          }

          if (msg.type === 'vision_game_started') {
            setVisionGameStarted(true);
            addLogRef.current('info', `Placement confirme (${msg.source}, ${msg.pieces_count} pieces)`);
          }

          if (msg.type === 'resume_confirmation_needed') {
            setResumeConfirmation({
              pieceName: msg.piece_name || 'Pièce',
              fromSq: msg.from_sq || '?',
              toSq: msg.to_sq || '?',
              player: msg.player === 'human' ? 'human' : 'robot',
            });
            addLog('info', `Replacez le ${msg.piece_name} en ${msg.to_sq} et confirmez`);
          }

          if (msg.type === 'vision_anomaly') {
            addLogRef.current('warning', msg.message || 'Anomalie vision detectee');
            const suggestions: string[] = [];
            if (msg.suggestions) {
              for (const s of msg.suggestions) {
                addLogRef.current('warning', s);
                suggestions.push(s);
              }
            }
            setIllegalMoveAlert({
              message: msg.message || 'Anomalie vision detectee',
              suggestions,
              timestamp: Date.now(),
            });
          }

          if (msg.type === 'move_undone') {
            setFen(msg.fen);
            setIsWhiteTurn(msg.fen.split(' ')[1] === 'w');
          }

          if (msg.type === 'goto_turn_complete') {
            setFen(msg.fen);
            setIsWhiteTurn(msg.fen.split(' ')[1] === 'w');
            setIsGameOver(false);
            setGameResult(null);
            setRobotStatus('idle');
            setIsReplacingBoard(false);
            if (onGotoTurnCompleteRef.current) {
              onGotoTurnCompleteRef.current(msg.turn, msg.fen);
            }
          }

          if (msg.type === 'promotion_required') {
            setIsPromotionPending(true);
            setPromotionSquare(msg.square);
            setPromotionColor(msg.color);
            addLogRef.current('info', `Promotion requise en ${msg.square}. Placez une Dame.`);
          }

          if (msg.type === 'board_replaced') {
            setIsReplacingBoard(false);
            if (!isDemoModeRef.current) {
              setFen(msg.fen);
              addLogRef.current('info', 'Plateau replace avec succes');
            }
          }

          if (msg.type === 'demo_started') {
            setIsDemoMode(true);
            isDemoModeRef.current = true;
            setDemoCycle(0);
            setDemoMoveCount(0);
            setDemoMovesPerCycle(msg.moves_per_cycle || 10);
            addLogRef.current('info', `Mode démo démarré (${msg.moves_per_cycle} coups/cycle)`);
          }

          if (msg.type === 'demo_cycle_started') {
            setDemoCycle(msg.cycle || 0);
            setDemoMoveCount(0);
            setFen(INITIAL_FEN);
            setIsWhiteTurn(true);
            setIsGameOver(false);
            setGameResult(null);
          }

          if (msg.type === 'demo_move') {
            setDemoMoveCount(msg.move_count || 0);
          }

          if (msg.type === 'demo_resetting') {
            setIsReplacingBoard(true);
          }

          if (msg.type === 'demo_stopped') {
            setIsDemoMode(false);
            isDemoModeRef.current = false;
            setDemoCycle(0);
            setDemoMoveCount(0);
            setIsReplacingBoard(false);
            addLogRef.current('info', 'Mode démo arrêté');
          }
        } catch { /* ignore parse errors */ }
      };

      ws.onclose = () => {
        setRobotStatus('disconnected');
        // Reconnexion automatique apres 3s
        reconnectTimer = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        setRobotStatus('disconnected');
      };

      wsRef.current = ws;
    };

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      if (wsRef.current) {
        wsRef.current.onclose = null; // Éviter le trigger de reconnexion lors du démontage
        wsRef.current.close();
      }
    };
  }, []); // Dépendances vides pour ne connecter qu'une seule fois

  // --- Init game via API ---
  const initGame = useCallback(async (difficulty: string) => {
    try {
      const res = await fetch(`${API_BASE}/game/new`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ difficulty }),
      });
      const data = await res.json();
      if (data.success) {
        setFen(data.fen);
        setIsWhiteTurn(true);
        setIsGameOver(false);
        setGameResult(null);
        setMoveEvaluations([]);
        setAcplScore(0);
        setRobotStatus('idle');
        addLogRef.current('info', `Nouvelle partie - Difficulte: ${difficulty}`);
      }
    } catch (e) {
      addLogRef.current('error', 'Erreur connexion API pour nouvelle partie');
    }
  }, []);

  // --- Human move via API ---
  const onMove = useCallback(async (from: string, to: string): Promise<boolean> => {
    try {
      // Identifier la piece pour le log
      const board = fenToBoard(fen);
      const piece = board[from];
      if (!piece) {
        addLogRef.current('error', 'Aucune piece a deplacer');
        return false;
      }

      setRobotStatus('moving');

      const res = await fetch(`${API_BASE}/game/move/human`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_square: from, to_square: to }),
      });
      const data = await res.json();

      if (!data.success) {
        addLogRef.current('error', data.error || 'Coup illegal');
        setRobotStatus('idle');
        return false;
      }

      // Le WebSocket va mettre a jour le FEN, mais on le fait aussi ici pour la reactivite
      const pieceName = getPieceName(piece);
      addLogRef.current('player', `Vous jouez: ${data.san || from + ' -> ' + to}`);
      onMoveCompleteRef.current({ from, to, piece: pieceName, player: 'human' });

      // Verifier fin de partie
      if (data.game_over) {
        setIsGameOver(true);
        const result = data.result as string;
        if (result.includes('Blancs')) setGameResult('win');
        else if (result.includes('Noirs')) setGameResult('lose');
        else setGameResult('draw');
        return true;
      }

      // Declencher le coup du robot
      setRobotStatus('thinking');
      triggerRobotMove();

      return true;
    } catch (e) {
      addLogRef.current('error', 'Erreur connexion API');
      setRobotStatus('error');
      return false;
    }
  }, [fen]);

  // --- Robot move via API ---
  const triggerRobotMove = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/game/move/robot`, { method: 'POST' });
      const data = await res.json();

      if (!data.success) {
        addLogRef.current('error', data.error || 'Erreur coup robot');
        setRobotStatus('idle');
        return;
      }

      // Le WebSocket diffuse deja le coup, mais on met a jour aussi directement
      if (data.game_over) {
        setIsGameOver(true);
        const result = data.result as string;
        if (result.includes('Blancs')) setGameResult('win');
        else if (result.includes('Noirs')) setGameResult('lose');
        else setGameResult('draw');
      }

    } catch (e) {
      addLogRef.current('error', 'Erreur connexion API pour coup robot');
      setRobotStatus('error');
    }
  }, []);

  // --- Legal moves : backend en priorité, fallback local chess.js ---
  const getLegalMoves = useCallback(async (square: string): Promise<string[]> => {
    // Calcul local immédiat depuis le FEN courant (toujours disponible)
    const computeLocal = (): string[] => {
      try {
        const chess = new Chess(fenRef.current);
        // cast en any pour éviter les problèmes de surcharge TypeScript verbose
        const moves = chess.moves({ square: square as any, verbose: true }) as any[];
        return moves.map((m: any) => m.to as string);
      } catch {
        return [];
      }
    };

    try {
      const res = await fetch(`${API_BASE}/game/legal-moves/${square}`);
      if (!res.ok) return computeLocal();
      const data = await res.json();
      // Si le backend répond vide (partie non initialisée), fallback local
      const backendMoves: string[] = data.moves || [];
      return backendMoves.length > 0 ? backendMoves : computeLocal();
    } catch {
      // Backend injoignable : calcul purement local
      return computeLocal();
    }
  }, []);

  // --- Best move via API ---
  const getBestMove = useCallback(async (): Promise<{ from: string; to: string } | null> => {
    try {
      const res = await fetch(`${API_BASE}/game/best-move`);
      const data = await res.json();
      if (data.success) {
        return { from: data.from, to: data.to };
      }
      return null;
    } catch {
      return null;
    }
  }, []);

  // --- Confirm placement ---
  const confirmPlacement = useCallback(async (useCamera: boolean): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/vision/confirm-placement`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ use_camera: useCamera }),
      });
      const data = await res.json();
      if (data.success) {
        setVisionGameStarted(true);
        return true;
      }
      return false;
    } catch {
      addLogRef.current('error', 'Erreur confirmation placement');
      return false;
    }
  }, []);

  // --- Replace board via API ---
  const replaceBoard = useCallback(async (): Promise<boolean> => {
    try {
      setIsReplacingBoard(true);
      setRobotStatus('replacing');
      const res = await fetch(`${API_BASE}/game/replace-board`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        addLogRef.current('info', 'Replacement du plateau demarre');
        return true;
      } else {
        addLogRef.current('error', data.error || 'Erreur lors du replacement');
        setIsReplacingBoard(false);
        setRobotStatus('idle');
        return false;
      }
    } catch {
      addLogRef.current('error', 'Erreur connexion API pour replacement');
      setIsReplacingBoard(false);
      setRobotStatus('error');
      return false;
    }
  }, []);

  // --- Confirm promotion ---
  const confirmPromotion = useCallback(async (from_sq: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/game/confirm-promotion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_sq }),
      });
      const data = await res.json();
      if (data.success) {
        setIsPromotionPending(false);
        setPromotionSquare(null);
        setPromotionColor(null);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }, []);

  // --- Reconnect Robot ---
  const reconnectRobot = useCallback(async (): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/robot/reconnect`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setRobotStatus('idle');
        addLogRef.current('info', 'Robot reconnecte avec succes');
        return true;
      }
      return false;
    } catch {
      addLogRef.current('error', 'Erreur lors de la reconnexion du robot');
      return false;
    }
  }, []);

  // --- Reset game ---
  const resetGame = useCallback(() => {
    setFen(INITIAL_FEN);
    setIsWhiteTurn(true);
    setIsGameOver(false);
    setGameResult(null);
    setRobotStatus('idle');
    setMoveEvaluations([]);
    setAcplScore(0);
    setVisionGameStarted(false);
    setIllegalMoveAlert(null);
    setIsReplacingBoard(false);
    setIsPromotionPending(false);
    setPromotionSquare(null);
    setPromotionColor(null);
    addLogRef.current('info', 'Partie reinitialisee');
  }, []);

  const dismissIllegalAlert = useCallback(() => {
    setIllegalMoveAlert(null);
  }, []);

  // --- Confirm resume after pause via API ---
  const confirmResume = useCallback(async (): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/game/confirm-resume`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setResumeConfirmation(null);
      }
      return data.success;
    } catch {
      addLogRef.current('error', 'Erreur confirmation reprise');
      return false;
    }
  }, []);

  // --- Undo last move via API ---
  const undoLastMove = useCallback(async (): Promise<number> => {
    try {
      const res = await fetch(`${API_BASE}/game/undo-move`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setFen(data.fen);
        setIsWhiteTurn(data.fen.split(' ')[1] === 'w');
        return data.moves_undone || 0;
      } else {
        addLogRef.current('warning', data.error || 'Impossible d\'annuler le coup');
        return 0;
      }
    } catch {
      addLogRef.current('error', 'Erreur connexion API pour annuler coup');
      return 0;
    }
  }, []);

  // --- Demo mode ---
  const startDemo = useCallback(async (movesPerCycle = 10, delayBetweenMoves = 4.0): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/game/demo/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ moves_per_cycle: movesPerCycle, delay_between_moves: delayBetweenMoves }),
      });
      const data = await res.json();
      if (!data.success) addLogRef.current('error', data.error || 'Erreur démarrage démo');
      return data.success;
    } catch {
      addLogRef.current('error', 'Erreur connexion API pour démo');
      return false;
    }
  }, []);

  const stopDemo = useCallback(async (): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/game/demo/stop`, { method: 'POST' });
      const data = await res.json();
      return data.success;
    } catch {
      addLogRef.current('error', 'Erreur connexion API pour arrêt démo');
      return false;
    }
  }, []);

  // --- Goto turn (retour arrière physique à un tour donné) ---
  const gotoTurn = useCallback(async (turn: number): Promise<boolean> => {
    try {
      addLogRef.current('info', `Retour au tour ${turn} en cours...`);
      const res = await fetch(`${API_BASE}/game/goto-turn`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ turn }),
      });
      const data = await res.json();
      if (!data.success) {
        addLogRef.current('error', data.error || 'Échec du retour arrière');
      }
      return data.success;
    } catch {
      addLogRef.current('error', 'Erreur connexion API pour retour arrière');
      return false;
    }
  }, []);

  // --- Enter correction mode (undo + enable correction UI) ---
  const enterCorrectionMode = useCallback(async (): Promise<number> => {
    const count = await undoLastMove();
    if (count > 0) {
      setIsCorrectionMode(true);
    }
    return count;
  }, [undoLastMove]);

  // --- Exit correction mode without playing a correction ---
  const exitCorrectionMode = useCallback(() => {
    setIsCorrectionMode(false);
  }, []);

  // --- Play corrected move (vision-style, no physical robot movement for human piece) ---
  const correctMove = useCallback(async (from: string, to: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/game/correct-move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_sq: from, to_sq: to }),
      });
      const data = await res.json();
      if (data.success) {
        setIsCorrectionMode(false);
      } else {
        addLogRef.current('error', data.error || 'Coup corrigé illégal');
      }
      return data.success;
    } catch {
      addLogRef.current('error', 'Erreur connexion API pour correction de coup');
      return false;
    }
  }, []);


  return {
    fen,
    isWhiteTurn,
    isGameOver,
    gameResult,
    robotStatus,
    acplScore,
    moveEvaluations,
    visionState,
    visionGameStarted,
    illegalMoveAlert,
    isReplacingBoard,
    isPromotionPending,
    promotionSquare,
    promotionColor,
    setRobotStatus,
    onMove,
    getLegalMoves,
    getBestMove,
    resetGame,
    initGame,
    confirmPlacement,
    dismissIllegalAlert,
    replaceBoard,
    confirmPromotion,
    reconnectRobot,
    resumeConfirmation,
    confirmResume,
    isCorrectionMode,
    undoLastMove,
    enterCorrectionMode,
    exitCorrectionMode,
    correctMove,
    isDemoMode,
    demoCycle,
    demoMoveCount,
    demoMovesPerCycle,
    startDemo,
    stopDemo,
    gotoTurn,
  };
}
