// hooks/useChessRobot.ts
import { useState, useEffect, useCallback, useRef } from 'react';

const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

export type RobotStatus = 'idle' | 'thinking' | 'moving' | 'error' | 'disconnected';
export type LogType = 'info' | 'robot' | 'player' | 'warning' | 'error';

export interface LogEntry {
  id: string;
  timestamp: Date;
  type: LogType;
  message: string;
}

export interface ChessMove {
  id: string;
  from: string;
  to: string;
  san: string;
  player: 'human' | 'robot';
  timestamp: Date;
  evaluation?: number;
}

interface UseChessRobotReturn {
  // État
  connected: boolean;
  robotConnected: boolean;
  status: RobotStatus;
  fen: string;
  isWhiteTurn: boolean;
  isGameOver: boolean;
  gameResult: string | null;
  logs: LogEntry[];
  moves: ChessMove[];
  
  // Actions
  newGame: (difficulty: string) => Promise<void>;
  playHumanMove: (from: string, to: string) => Promise<boolean>;
  playRobotMove: () => Promise<boolean>;
  getLegalMoves: (square: string) => Promise<string[]>;
  getBestMove: () => Promise<{ from: string; to: string } | null>;

  // Helpers
  addLog: (type: LogType, message: string) => void;
}

export function useChessRobot(): UseChessRobotReturn {
  const [connected, setConnected] = useState(false);
  const [robotConnected, setRobotConnected] = useState(false);
  const [status, setStatus] = useState<RobotStatus>('disconnected');
  const [fen, setFen] = useState('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
  const [isWhiteTurn, setIsWhiteTurn] = useState(true);
  const [isGameOver, setIsGameOver] = useState(false);
  const [gameResult, setGameResult] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [moves, setMoves] = useState<ChessMove[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Ajouter un log
  const addLog = useCallback((type: LogType, message: string) => {
    const newLog: LogEntry = {
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date(),
      type,
      message
    };
    setLogs(prev => [newLog, ...prev].slice(0, 100));
  }, []);

  // Ajouter un mouvement
  const addMove = useCallback((move: Omit<ChessMove, 'id' | 'timestamp'>) => {
    const newMove: ChessMove = {
      ...move,
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date()
    };
    setMoves(prev => [...prev, newMove]);
  }, []);

  // Connexion WebSocket
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);
      addLog('info', 'Connexion au serveur établie');
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        switch (message.type) {
          case 'connected':
            setStatus(message.status || 'idle');
            setFen(message.fen);
            setRobotConnected(message.robot_connected);
            if (message.robot_connected) {
              addLog('info', 'Robot UR5e connecté');
            } else {
              addLog('warning', 'Robot non connecté - Mode simulation');
            }
            break;

          case 'status':
            setStatus(message.status);
            if (message.message) {
              addLog('info', message.message);
            }
            break;

          case 'log':
            addLog(message.logType, message.message);
            break;

          case 'move':
            setFen(message.fen);
            setIsWhiteTurn(message.fen.split(' ')[1] === 'w');
            addMove({
              from: message.from,
              to: message.to,
              san: message.san,
              player: message.player,
              evaluation: message.evaluation
            });
            break;

          case 'game_over':
            setIsGameOver(true);
            setGameResult(message.result);
            addLog('info', `Partie terminée: ${message.result}`);
            break;

          case 'pong':
            // Réponse au ping
            break;
        }
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setConnected(false);
      setStatus('disconnected');
      addLog('warning', 'Connexion au serveur perdue');

      // Reconnexion automatique
      reconnectTimeoutRef.current = setTimeout(() => {
        connectWebSocket();
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      addLog('error', 'Erreur de connexion WebSocket');
    };

    wsRef.current = ws;
  }, [addLog, addMove]);

  // Connexion au démarrage
  useEffect(() => {
    connectWebSocket();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connectWebSocket]);

  // Ping périodique pour garder la connexion
  useEffect(() => {
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);

    return () => clearInterval(pingInterval);
  }, []);

  // Nouvelle partie
  const newGame = useCallback(async (difficulty: string) => {
    try {
      const response = await fetch(`${API_URL}/game/new`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ difficulty })
      });

      const data = await response.json();

      if (data.success) {
        setFen(data.fen);
        setIsWhiteTurn(true);
        setIsGameOver(false);
        setGameResult(null);
        setMoves([]);
        setLogs([]);
        addLog('info', `Nouvelle partie - Difficulté: ${difficulty}`);
      }
    } catch (e) {
      addLog('error', 'Erreur lors de la création de la partie');
    }
  }, [addLog]);

  // Jouer un coup humain
  const playHumanMove = useCallback(async (from: string, to: string): Promise<boolean> => {
    try {
      const response = await fetch(`${API_URL}/game/move/human`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_square: from, to_square: to })
      });

      const data = await response.json();

      if (!data.success) {
        addLog('warning', data.error || 'Coup invalide');
        return false;
      }

      return true;
    } catch (e) {
      addLog('error', 'Erreur lors de l\'envoi du coup');
      return false;
    }
  }, [addLog]);

  // Demander au robot de jouer
  const playRobotMove = useCallback(async (): Promise<boolean> => {
    try {
      const response = await fetch(`${API_URL}/game/move/robot`, {
        method: 'POST'
      });

      const data = await response.json();

      if (!data.success) {
        addLog('error', data.error || 'Erreur du robot');
        return false;
      }

      return true;
    } catch (e) {
      addLog('error', 'Erreur lors de la demande au robot');
      return false;
    }
  }, [addLog]);

  // Obtenir les coups légaux
  const getLegalMoves = useCallback(async (square: string): Promise<string[]> => {
    try {
      const response = await fetch(`${API_URL}/game/legal-moves/${square}`);
      const data = await response.json();
      return data.moves || [];
    } catch (e) {
      return [];
    }
  }, []);

  // Obtenir le meilleur coup
  const getBestMove = useCallback(async (): Promise<{ from: string; to: string } | null> => {
    try {
      const response = await fetch(`${API_URL}/game/best-move`);
      const data = await response.json();

      if (data.success) {
        return { from: data.from, to: data.to };
      }
      return null;
    } catch (e) {
      return null;
    }
  }, []);

  return {
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
    getBestMove,
    addLog
  };
}