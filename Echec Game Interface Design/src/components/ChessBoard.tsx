// components/ChessBoard.tsx
import { useState, useEffect } from 'react';
import type { RobotStatus } from '../hooks/useChessRobot';

interface ChessBoardProps {
  fen: string;
  isWhiteTurn: boolean;
  robotStatus: RobotStatus;
  isGameOver: boolean;
  onMove: (from: string, to: string) => Promise<boolean>;
  getLegalMoves: (square: string) => Promise<string[]>;
}

type Piece = string | null;

interface BoardState {
  [key: string]: Piece;
}

// Convertir FEN en état du plateau
function fenToBoard(fen: string): BoardState {
  const board: BoardState = {};
  const [position] = fen.split(' ');
  const rows = position.split('/');
  
  const pieceMap: { [key: string]: string } = {
    'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚', 'p': '♟',
    'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔', 'P': '♙'
  };
  
  const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
  
  rows.forEach((row, rowIndex) => {
    const rank = 8 - rowIndex;
    let fileIndex = 0;
    
    for (const char of row) {
      if (isNaN(parseInt(char))) {
        const square = `${files[fileIndex]}${rank}`;
        board[square] = pieceMap[char] || null;
        fileIndex++;
      } else {
        fileIndex += parseInt(char);
      }
    }
  });
  
  return board;
}

export function ChessBoard({ 
  fen, 
  isWhiteTurn, 
  robotStatus, 
  isGameOver,
  onMove,
  getLegalMoves 
}: ChessBoardProps) {
  const [board, setBoard] = useState<BoardState>({});
  const [selectedSquare, setSelectedSquare] = useState<string | null>(null);
  const [legalMoves, setLegalMoves] = useState<string[]>([]);
  const [lastMove, setLastMove] = useState<{ from: string; to: string } | null>(null);

  const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
  const ranks = ['8', '7', '6', '5', '4', '3', '2', '1'];

  // Mettre à jour le plateau quand le FEN change
  useEffect(() => {
    setBoard(fenToBoard(fen));
  }, [fen]);

  const handleSquareClick = async (square: string) => {
    // Désactiver si partie terminée ou robot en action
    if (isGameOver || robotStatus !== 'idle' || !isWhiteTurn) return;

    const piece = board[square];

    if (selectedSquare === null) {
      // Sélectionner une pièce blanche
      if (piece && ['♔', '♕', '♖', '♗', '♘', '♙'].includes(piece)) {
        setSelectedSquare(square);
        // Obtenir les coups légaux
        const moves = await getLegalMoves(square);
        setLegalMoves(moves);
      }
    } else {
      if (square === selectedSquare) {
        // Désélectionner
        setSelectedSquare(null);
        setLegalMoves([]);
      } else if (legalMoves.includes(square)) {
        // Jouer le coup
        const success = await onMove(selectedSquare, square);
        
        if (success) {
          setLastMove({ from: selectedSquare, to: square });
        }
        
        setSelectedSquare(null);
        setLegalMoves([]);
      } else if (piece && ['♔', '♕', '♖', '♗', '♘', '♙'].includes(piece)) {
        // Sélectionner une autre pièce
        setSelectedSquare(square);
        const moves = await getLegalMoves(square);
        setLegalMoves(moves);
      } else {
        // Clic invalide
        setSelectedSquare(null);
        setLegalMoves([]);
      }
    }
  };

  const isLightSquare = (file: string, rank: string) => {
    const fileIndex = files.indexOf(file);
    const rankIndex = ranks.indexOf(rank);
    return (fileIndex + rankIndex) % 2 === 0;
  };

  const isWhitePiece = (piece: string | null) => {
    return piece && ['♔', '♕', '♖', '♗', '♘', '♙'].includes(piece);
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700 h-full flex items-center justify-center">
      <div className="aspect-square w-full max-w-md max-h-full">
        <div className="relative h-full">
          {/* Board */}
          <div className="grid grid-cols-8 gap-0 border-4 border-slate-600 rounded-lg overflow-hidden shadow-2xl h-full">
            {ranks.map(rank => 
              files.map(file => {
                const square = `${file}${rank}`;
                const piece = board[square];
                const isLight = isLightSquare(file, rank);
                const isSelected = selectedSquare === square;
                const isLegalMove = legalMoves.includes(square);
                const isLastMoveSquare = lastMove && (lastMove.from === square || lastMove.to === square);
                const canSelect = isWhiteTurn && robotStatus === 'idle' && !isGameOver;

                return (
                  <button
                    key={square}
                    onClick={() => handleSquareClick(square)}
                    disabled={!canSelect}
                    className={`
                      aspect-square flex items-center justify-center text-3xl
                      transition-all duration-200 relative
                      ${isLight ? 'bg-amber-100' : 'bg-amber-800'}
                      ${isSelected ? 'ring-4 ring-cyan-400 ring-inset' : ''}
                      ${isLastMoveSquare ? 'bg-yellow-400/50' : ''}
                      ${isLegalMove ? 'bg-green-400/40' : ''}
                      ${canSelect ? 'hover:brightness-110 cursor-pointer' : 'cursor-not-allowed'}
                    `}
                  >
                    {/* Indicateur de coup légal */}
                    {isLegalMove && !piece && (
                      <div className="w-3 h-3 bg-green-500/60 rounded-full"></div>
                    )}
                    
                    {/* Pièce */}
                    {piece && (
                      <span className={`
                        drop-shadow-lg text-4xl
                        ${isWhitePiece(piece) ? 'text-white' : 'text-slate-900'}
                        ${isLegalMove ? 'ring-2 ring-red-500 rounded-full' : ''}
                      `}
                      style={{ textShadow: isWhitePiece(piece) ? '1px 1px 2px black' : 'none' }}
                      >
                        {piece}
                      </span>
                    )}
                    
                    {/* Coordonnées */}
                    {rank === '1' && (
                      <span className={`absolute bottom-0.5 right-1 text-xs font-bold ${isLight ? 'text-amber-800/40' : 'text-amber-100/40'}`}>
                        {file}
                      </span>
                    )}
                    {file === 'a' && (
                      <span className={`absolute top-0.5 left-1 text-xs font-bold ${isLight ? 'text-amber-800/40' : 'text-amber-100/40'}`}>
                        {rank}
                      </span>
                    )}
                  </button>
                );
              })
            )}
          </div>

          {/* Overlay de statut */}
          {(robotStatus === 'thinking' || robotStatus === 'moving') && (
            <div className="absolute inset-0 bg-slate-900/80 backdrop-blur-sm rounded-lg flex items-center justify-center">
              <div className="text-center">
                <div className="w-16 h-16 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                <div className="text-white text-xl font-semibold">
                  {robotStatus === 'thinking' && 'Robot réfléchit...'}
                  {robotStatus === 'moving' && 'Robot en mouvement...'}
                </div>
                <div className="text-slate-400 text-sm mt-2">
                  {robotStatus === 'thinking' && 'Analyse de la position'}
                  {robotStatus === 'moving' && 'Déplacement de la pièce'}
                </div>
              </div>
            </div>
          )}

          {/* Overlay d'attente du tour */}
          {!isWhiteTurn && robotStatus === 'idle' && !isGameOver && (
            <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm rounded-lg flex items-center justify-center">
              <div className="text-center">
                <div className="text-white text-xl font-semibold mb-2">
                  Tour du robot
                </div>
                <div className="text-slate-400 text-sm">
                  En attente du coup...
                </div>
              </div>
            </div>
          )}

          {/* Overlay fin de partie */}
          {isGameOver && (
            <div className="absolute inset-0 bg-slate-900/90 backdrop-blur-sm rounded-lg flex items-center justify-center">
              <div className="text-center">
                <div className="text-4xl mb-4">🏆</div>
                <div className="text-white text-2xl font-bold">
                  Partie terminée
                </div>
              </div>
            </div>
          )}

          {/* Overlay erreur */}
          {robotStatus === 'error' && (
            <div className="absolute inset-0 bg-red-900/80 backdrop-blur-sm rounded-lg flex items-center justify-center">
              <div className="text-center">
                <div className="text-4xl mb-4">⚠️</div>
                <div className="text-white text-xl font-semibold">
                  Erreur détectée
                </div>
                <div className="text-red-200 text-sm mt-2">
                  Vérifiez la connexion du robot
                </div>
              </div>
            </div>
          )}

          {/* Overlay déconnecté */}
          {robotStatus === 'disconnected' && (
            <div className="absolute inset-0 bg-slate-900/90 backdrop-blur-sm rounded-lg flex items-center justify-center">
              <div className="text-center">
                <div className="w-12 h-12 border-4 border-slate-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                <div className="text-white text-xl font-semibold">
                  Connexion au serveur...
                </div>
                <div className="text-slate-400 text-sm mt-2">
                  Assurez-vous que l'API est lancée
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
