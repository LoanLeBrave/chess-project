import { useState, useCallback } from 'react';

export type RobotStatus = 'idle' | 'thinking' | 'moving' | 'error' | 'disconnected';

export interface UseChessRobotReturn {
  fen: string;
  isWhiteTurn: boolean;
  isGameOver: boolean;
  robotStatus: RobotStatus;
  setRobotStatus: (status: RobotStatus) => void;
  onMove: (from: string, to: string) => Promise<boolean>;
  getLegalMoves: (square: string) => Promise<string[]>;
  getBestMove: () => Promise<{ from: string; to: string } | null>;
  resetGame: () => void;
}

const INITIAL_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

// Fonction utilitaire pour parser le FEN
function parseFEN(fen: string) {
  const [position, turn] = fen.split(' ');
  return { position, turn };
}

// Fonction utilitaire pour créer un board depuis le FEN
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

// Fonction utilitaire pour convertir un board en FEN
function boardToFEN(board: { [key: string]: string }, isWhiteTurn: boolean): string {
  const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
  const ranks = ['8', '7', '6', '5', '4', '3', '2', '1'];
  
  let fenPosition = '';
  for (const rank of ranks) {
    let emptyCount = 0;
    for (const file of files) {
      const square = `${file}${rank}`;
      const piece = board[square];
      if (piece) {
        if (emptyCount > 0) {
          fenPosition += emptyCount;
          emptyCount = 0;
        }
        fenPosition += piece;
      } else {
        emptyCount++;
      }
    }
    if (emptyCount > 0) {
      fenPosition += emptyCount;
    }
    if (rank !== '1') {
      fenPosition += '/';
    }
  }
  
  const turn = isWhiteTurn ? 'w' : 'b';
  return `${fenPosition} ${turn} KQkq - 0 1`;
}

// Fonction pour obtenir le nom de la pièce
function getPieceName(piece: string): string {
  const names: { [key: string]: string } = {
    'K': 'Roi', 'Q': 'Dame', 'R': 'Tour', 'B': 'Fou', 'N': 'Cavalier', 'P': 'Pion',
    'k': 'Roi', 'q': 'Dame', 'r': 'Tour', 'b': 'Fou', 'n': 'Cavalier', 'p': 'Pion'
  };
  return names[piece] || 'Pièce';
}

/**
 * Hook personnalisé pour gérer la logique du jeu d'échecs avec le robot
 * TODO: Intégrer avec le vrai moteur d'échecs (Stockfish) et l'API du robot UR7e
 */
export function useChessRobot(
  addLog: (type: 'info' | 'warning' | 'error' | 'robot' | 'player', message: string) => void,
  onMoveComplete: (move: { from: string; to: string; piece: string; player: 'human' | 'robot' }) => void
): UseChessRobotReturn {
  const [fen, setFen] = useState(INITIAL_FEN);
  const [isWhiteTurn, setIsWhiteTurn] = useState(true);
  const [isGameOver, setIsGameOver] = useState(false);
  const [robotStatus, setRobotStatus] = useState<RobotStatus>('idle');

  /**
   * Effectue un mouvement sur l'échiquier
   */
  const onMove = useCallback(async (from: string, to: string): Promise<boolean> => {
    try {
      const board = fenToBoard(fen);
      const piece = board[from];
      
      if (!piece) {
        addLog('error', 'Aucune pièce à déplacer');
        return false;
      }

      // Vérifier que c'est une pièce blanche
      const whitePieces = ['K', 'Q', 'R', 'B', 'N', 'P'];
      if (!whitePieces.includes(piece)) {
        addLog('error', 'Ce n\'est pas votre pièce');
        return false;
      }

      // Effectuer le mouvement
      const capturedPiece = board[to];
      board[to] = piece;
      delete board[from];

      // Mettre à jour le FEN
      const newFen = boardToFEN(board, false);
      setFen(newFen);

      const pieceName = getPieceName(piece);
      let moveDesc = `${pieceName} ${from.toUpperCase()} → ${to.toUpperCase()}`;
      if (capturedPiece) {
        moveDesc += ` (capture ${getPieceName(capturedPiece)})`;
      }
      
      addLog('player', `Vous jouez: ${moveDesc}`);

      // Notifier le coup
      onMoveComplete({
        from,
        to,
        piece: pieceName,
        player: 'human'
      });

      // Changer de tour
      setIsWhiteTurn(false);

      // Déclencher le coup du robot après un délai
      setTimeout(() => {
        simulateRobotMove(newFen);
      }, 500);

      return true;
    } catch (error) {
      addLog('error', 'Erreur lors du mouvement');
      return false;
    }
  }, [fen, addLog, onMoveComplete]);

  /**
   * Simule un coup du robot
   */
  const simulateRobotMove = useCallback(async (currentFen: string) => {
    setRobotStatus('thinking');
    addLog('robot', 'Robot analyse la position...');

    // Simuler le temps de réflexion
    await new Promise(resolve => setTimeout(resolve, 1500));

    setRobotStatus('moving');
    addLog('robot', 'Mouvement du bras robotique en cours...');

    // Trouver un coup aléatoire pour le robot (pièces noires)
    const board = fenToBoard(currentFen);
    const blackPieces = Object.entries(board).filter(([_, piece]) => 
      ['k', 'q', 'r', 'b', 'n', 'p'].includes(piece)
    );

    if (blackPieces.length > 0) {
      // Choisir une pièce aléatoire
      const [fromSquare, piece] = blackPieces[Math.floor(Math.random() * blackPieces.length)];
      
      // Trouver les cases vides ou avec des pièces blanches (pour capturer)
      const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
      const ranks = ['1', '2', '3', '4', '5', '6', '7', '8'];
      const allSquares = files.flatMap(f => ranks.map(r => `${f}${r}`));
      const possibleMoves = allSquares.filter(sq => {
        const targetPiece = board[sq];
        return !targetPiece || ['K', 'Q', 'R', 'B', 'N', 'P'].includes(targetPiece);
      });

      if (possibleMoves.length > 0) {
        const toSquare = possibleMoves[Math.floor(Math.random() * possibleMoves.length)];
        
        // Simuler le mouvement physique
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Effectuer le mouvement
        const capturedPiece = board[toSquare];
        board[toSquare] = piece;
        delete board[fromSquare];

        // Mettre à jour le FEN
        const newFen = boardToFEN(board, true);
        setFen(newFen);

        const pieceName = getPieceName(piece);
        let moveDesc = `${pieceName} ${fromSquare.toUpperCase()} → ${toSquare.toUpperCase()}`;
        if (capturedPiece) {
          moveDesc += ` (capture ${getPieceName(capturedPiece)})`;
        }

        onMoveComplete({
          from: fromSquare,
          to: toSquare,
          piece: pieceName,
          player: 'robot'
        });

        addLog('robot', `Robot joue: ${moveDesc}`);
        setRobotStatus('idle');
        setIsWhiteTurn(true);
      } else {
        addLog('error', 'Aucun coup possible pour le robot');
        setRobotStatus('idle');
        setIsWhiteTurn(true);
      }
    }
  }, [addLog, onMoveComplete]);

  /**
   * Récupère tous les coups légaux pour une case donnée
   * TODO: Intégrer avec Stockfish pour les vrais coups légaux
   */
  const getLegalMoves = useCallback(async (square: string): Promise<string[]> => {
    await new Promise(resolve => setTimeout(resolve, 50));
    
    const board = fenToBoard(fen);
    const piece = board[square];
    
    if (!piece) return [];

    // Simulation simple - retourner des cases vides ou avec des pièces adverses
    const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
    const ranks = ['1', '2', '3', '4', '5', '6', '7', '8'];
    const allSquares = files.flatMap(f => ranks.map(r => `${f}${r}`));
    
    const isWhitePiece = ['K', 'Q', 'R', 'B', 'N', 'P'].includes(piece);
    const validMoves = allSquares.filter(sq => {
      if (sq === square) return false;
      const targetPiece = board[sq];
      
      if (!targetPiece) return true; // Case vide
      
      // Peut capturer une pièce adverse
      const targetIsWhite = ['K', 'Q', 'R', 'B', 'N', 'P'].includes(targetPiece);
      return isWhitePiece !== targetIsWhite;
    });

    // Limiter à quelques coups aléatoires pour la démo
    const shuffled = validMoves.sort(() => 0.5 - Math.random());
    return shuffled.slice(0, 8);
  }, [fen]);

  /**
   * Récupère le meilleur coup selon Stockfish
   * TODO: Intégrer avec Stockfish
   */
  const getBestMove = useCallback(async (): Promise<{ from: string; to: string } | null> => {
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const board = fenToBoard(fen);
    const whitePieces = Object.entries(board).filter(([_, piece]) => 
      ['K', 'Q', 'R', 'B', 'N', 'P'].includes(piece)
    );

    if (whitePieces.length === 0) return null;

    // Choisir une pièce aléatoire
    const [from] = whitePieces[Math.floor(Math.random() * whitePieces.length)];
    const legalMoves = await getLegalMoves(from);
    
    if (legalMoves.length === 0) return null;
    
    return {
      from,
      to: legalMoves[0]
    };
  }, [fen, getLegalMoves]);

  /**
   * Réinitialise la partie
   */
  const resetGame = useCallback(() => {
    setFen(INITIAL_FEN);
    setIsWhiteTurn(true);
    setIsGameOver(false);
    setRobotStatus('idle');
    addLog('info', 'Nouvelle partie initialisée');
  }, [addLog]);

  return {
    fen,
    isWhiteTurn,
    isGameOver,
    robotStatus,
    setRobotStatus,
    onMove,
    getLegalMoves,
    getBestMove,
    resetGame
  };
}
