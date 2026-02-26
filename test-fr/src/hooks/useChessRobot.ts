import { useState, useCallback, useEffect, useRef } from 'react';

export type RobotStatus = 'idle' | 'thinking' | 'moving' | 'error' | 'disconnected';

export interface MoveEvaluation {
  move: string;
  centipawnLoss: number;
}

export interface VisionState {
  board: { [square: string]: string };
  confidence: { [square: string]: number };
  pieces_count: number;
  game_started: boolean;
  reference_set: boolean;
}

export interface IllegalMoveAlert {
  message: string;
  suggestions: string[];
  timestamp: number;
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
  setRobotStatus: (status: RobotStatus) => void;
  onMove: (from: string, to: string) => Promise<boolean>;
  getLegalMoves: (square: string) => Promise<string[]>;
  getBestMove: () => Promise<{ from: string; to: string } | null>;
  resetGame: () => void;
  initGame: (difficulty: string) => Promise<void>;
  confirmPlacement: (useCamera: boolean) => Promise<boolean>;
  dismissIllegalAlert: () => void;
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
  onMoveComplete: (move: { from: string; to: string; piece: string; player: 'human' | 'robot' }) => void
): UseChessRobotReturn {
  const [fen, setFen] = useState(INITIAL_FEN);
  const [isWhiteTurn, setIsWhiteTurn] = useState(true);
  const [isGameOver, setIsGameOver] = useState(false);
  const [gameResult, setGameResult] = useState<'win' | 'lose' | 'draw' | null>(null);
  const [robotStatus, setRobotStatus] = useState<RobotStatus>('disconnected');
  const [moveEvaluations, setMoveEvaluations] = useState<MoveEvaluation[]>([]);
  const [acplScore, setAcplScore] = useState(0);
  const [visionState, setVisionState] = useState<VisionState | null>(null);
  const [visionGameStarted, setVisionGameStarted] = useState(false);
  const [illegalMoveAlert, setIllegalMoveAlert] = useState<IllegalMoveAlert | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // --- WebSocket ---
  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        setRobotStatus('idle');
        addLog('info', 'Connexion WebSocket etablie');
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === 'status') {
            const statusMap: { [key: string]: RobotStatus } = {
              'idle': 'idle', 'thinking': 'thinking', 'moving': 'moving',
              'error': 'error', 'paused': 'idle',
            };
            setRobotStatus(statusMap[msg.status] || 'idle');
          }

          if (msg.type === 'move') {
            setFen(msg.fen);
            setIsWhiteTurn(msg.fen.split(' ')[1] === 'w');

            if (msg.player === 'robot') {
              onMoveComplete({
                from: msg.from,
                to: msg.to,
                piece: msg.san ? msg.san[0] : 'Piece',
                player: 'robot'
              });
              addLog('robot', `Robot joue: ${msg.san || msg.from + ' -> ' + msg.to}`);
              setRobotStatus('idle');
            } else if (msg.player === 'human') {
              // Coup humain detecte par la vision camera
              onMoveComplete({
                from: msg.from,
                to: msg.to,
                piece: msg.san ? msg.san[0] : 'Piece',
                player: 'human'
              });
              addLog('player', `Coup detecte: ${msg.san || msg.from + ' -> ' + msg.to}`);
              setRobotStatus('thinking');
            }
          }

          if (msg.type === 'game_over') {
            setIsGameOver(true);
            const result = msg.result as string;
            if (result.includes('Blancs')) {
              setGameResult('win');
            } else if (result.includes('Noirs')) {
              setGameResult('lose');
            } else {
              setGameResult('draw');
            }
            addLog('info', result);
          }

          if (msg.type === 'log') {
            addLog(msg.logType || 'info', msg.message);
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
            });
          }

          if (msg.type === 'vision_game_started') {
            setVisionGameStarted(true);
            addLog('info', `Placement confirme (${msg.source}, ${msg.pieces_count} pieces)`);
          }

          if (msg.type === 'vision_anomaly') {
            addLog('warning', msg.message || 'Anomalie vision detectee');
            const suggestions: string[] = [];
            if (msg.suggestions) {
              for (const s of msg.suggestions) {
                addLog('warning', s);
                suggestions.push(s);
              }
            }
            setIllegalMoveAlert({
              message: msg.message || 'Anomalie vision detectee',
              suggestions,
              timestamp: Date.now(),
            });
          }
        } catch { /* ignore parse errors */ }
      };

      ws.onclose = () => {
        setRobotStatus('disconnected');
        // Reconnexion automatique apres 3s
        setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        setRobotStatus('disconnected');
      };

      wsRef.current = ws;
    };

    connect();

    return () => {
      wsRef.current?.close();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
        addLog('info', `Nouvelle partie - Difficulte: ${difficulty}`);
      }
    } catch (e) {
      addLog('error', 'Erreur connexion API pour nouvelle partie');
    }
  }, [addLog]);

  // --- Human move via API ---
  const onMove = useCallback(async (from: string, to: string): Promise<boolean> => {
    try {
      // Identifier la piece pour le log
      const board = fenToBoard(fen);
      const piece = board[from];
      if (!piece) {
        addLog('error', 'Aucune piece a deplacer');
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
        addLog('error', data.error || 'Coup illegal');
        setRobotStatus('idle');
        return false;
      }

      // Le WebSocket va mettre a jour le FEN, mais on le fait aussi ici pour la reactivite
      const pieceName = getPieceName(piece);
      addLog('player', `Vous jouez: ${data.san || from + ' -> ' + to}`);
      onMoveComplete({ from, to, piece: pieceName, player: 'human' });

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
      addLog('error', 'Erreur connexion API');
      setRobotStatus('error');
      return false;
    }
  }, [fen, addLog, onMoveComplete]);

  // --- Robot move via API ---
  const triggerRobotMove = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/game/move/robot`, { method: 'POST' });
      const data = await res.json();

      if (!data.success) {
        addLog('error', data.error || 'Erreur coup robot');
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

      // ACPL: utiliser l'evaluation du backend
      if (data.evaluation !== undefined) {
        const cpLoss = typeof data.evaluation === 'number' ? Math.abs(data.evaluation * 100) : 0;
        setMoveEvaluations(prev => {
          const updated = [...prev, { move: `${data.from}-${data.to}`, centipawnLoss: cpLoss }];
          const total = updated.reduce((sum, e) => sum + e.centipawnLoss, 0);
          setAcplScore(Math.round(total / updated.length));
          return updated;
        });
      }
    } catch (e) {
      addLog('error', 'Erreur connexion API pour coup robot');
      setRobotStatus('error');
    }
  }, [addLog]);

  // --- Legal moves via API ---
  const getLegalMoves = useCallback(async (square: string): Promise<string[]> => {
    try {
      const res = await fetch(`${API_BASE}/game/legal-moves/${square}`);
      const data = await res.json();
      return data.moves || [];
    } catch {
      return [];
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
      addLog('error', 'Erreur confirmation placement');
      return false;
    }
  }, [addLog]);

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
    addLog('info', 'Partie reinitialisee');
  }, [addLog]);

  const dismissIllegalAlert = useCallback(() => {
    setIllegalMoveAlert(null);
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
    setRobotStatus,
    onMove,
    getLegalMoves,
    getBestMove,
    resetGame,
    initGame,
    confirmPlacement,
    dismissIllegalAlert,
  };
}
