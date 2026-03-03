import { useState, useEffect } from 'react';
import { Lightbulb } from 'lucide-react';
import type { RobotStatus, PiecesEliminees } from '../hooks/useChessRobot';

interface ChessBoardProps {
  fen: string;
  isWhiteTurn: boolean;
  robotStatus: RobotStatus;
  isGameOver: boolean;
  onMove: (from: string, to: string) => Promise<boolean>;
  getLegalMoves: (square: string) => Promise<string[]>;
  getBestMove: () => Promise<{ from: string; to: string } | null>;
  showVision?: boolean;
  visionBoard?: { [square: string]: string };
  visionConfidence?: { [square: string]: number };
  isCorrectionMode?: boolean;
  cemeteryBoard?: { [square: string]: string };
  piecesEliminees?: PiecesEliminees;
}

type PieceType = 'K' | 'Q' | 'R' | 'B' | 'N' | 'P' | 'k' | 'q' | 'r' | 'b' | 'n' | 'p' | null;
interface BoardState { [key: string]: PieceType; }

/**
 * Convertit pieces_eliminees en map {case_cimetiere: 'WP'/'BN'...}
 * pour afficher la vue Stockfish du cimetière.
 */
function piecesElimineeesToMap(pe: PiecesEliminees | undefined): { [square: string]: string } {
  if (!pe) return {};
  const map: { [square: string]: string } = {};
  for (const p of pe.blanches) {
    const typeChar = p.piece === 'N' ? 'N' : p.piece[0];
    map[p.case_cimetiere] = `W${typeChar}`;
  }
  for (const p of pe.noires) {
    const typeChar = p.piece === 'N' ? 'N' : p.piece[0];
    map[p.case_cimetiere] = `B${typeChar}`;
  }
  return map;
}

// Convertit un code vision ("WP", "BK", "BN"...) en cle PIECE_IMAGES ("P", "k", "n"...)
function visionCodeToPieceKey(code: string): string | null {
  if (!code || code.length < 2) return null;
  const color = code[0]; // "W" ou "B"
  const type = code[1];  // "P", "K", "Q", "R", "B", "N"
  if (color === 'W') return type.toUpperCase();
  if (color === 'B') return type.toLowerCase();
  return null;
}

// Pièces SVG style chess.com (utilise les images de lichess qui sont libres de droits)
const PIECE_IMAGES: { [key: string]: string } = {
  'K': 'https://images.chesscomfiles.com/chess-themes/pieces/neo/150/wk.png',
  'Q': 'https://images.chesscomfiles.com/chess-themes/pieces/neo/150/wq.png',
  'R': 'https://images.chesscomfiles.com/chess-themes/pieces/neo/150/wr.png',
  'B': 'https://images.chesscomfiles.com/chess-themes/pieces/neo/150/wb.png',
  'N': 'https://images.chesscomfiles.com/chess-themes/pieces/neo/150/wn.png',
  'P': 'https://images.chesscomfiles.com/chess-themes/pieces/neo/150/wp.png',
  'k': 'https://images.chesscomfiles.com/chess-themes/pieces/neo/150/bk.png',
  'q': 'https://images.chesscomfiles.com/chess-themes/pieces/neo/150/bq.png',
  'r': 'https://images.chesscomfiles.com/chess-themes/pieces/neo/150/br.png',
  'b': 'https://images.chesscomfiles.com/chess-themes/pieces/neo/150/bb.png',
  'n': 'https://images.chesscomfiles.com/chess-themes/pieces/neo/150/bn.png',
  'p': 'https://images.chesscomfiles.com/chess-themes/pieces/neo/150/bp.png',
};

function fenToBoard(fen: string): BoardState {
  const board: BoardState = {};
  const [position] = fen.split(' ');
  const rows = position.split('/');
  const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];

  rows.forEach((row, rowIndex) => {
    const rank = 8 - rowIndex;
    let fileIndex = 0;
    for (const char of row) {
      if (isNaN(parseInt(char))) {
        board[`${files[fileIndex]}${rank}`] = char as PieceType;
        fileIndex++;
      } else {
        fileIndex += parseInt(char);
      }
    }
  });
  return board;
}

export function ChessBoard({
  fen, isWhiteTurn, robotStatus, isGameOver, onMove, getLegalMoves, getBestMove,
  showVision, visionBoard, visionConfidence, isCorrectionMode,
  cemeteryBoard, piecesEliminees,
}: ChessBoardProps) {
  const [board, setBoard] = useState<BoardState>({});
  const [selectedSquare, setSelectedSquare] = useState<string | null>(null);
  const [legalMoves, setLegalMoves] = useState<string[]>([]);
  const [lastMove, setLastMove] = useState<{ from: string; to: string } | null>(null);

  const [showHelpOnClick, setShowHelpOnClick] = useState(true);
  const [showAllMoves, setShowAllMoves] = useState(false);
  const [allWhiteMoves, setAllWhiteMoves] = useState<{ [key: string]: string[] }>({});
  const [bestMove, setBestMove] = useState<{ from: string; to: string } | null>(null);
  const [isLoadingAllMoves, setIsLoadingAllMoves] = useState(false);
  const [isLoadingBestMove, setIsLoadingBestMove] = useState(false);

  const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
  const ranks = ['8', '7', '6', '5', '4', '3', '2', '1'];

  useEffect(() => {
    setBoard(fenToBoard(fen));
    setBestMove(null);
    setShowAllMoves(false);
    setAllWhiteMoves({});
    setSelectedSquare(null);
    setLegalMoves([]);
  }, [fen]);

  const loadAllWhiteMoves = async () => {
    setIsLoadingAllMoves(true);
    const moves: { [key: string]: string[] } = {};
    const currentBoard = fenToBoard(fen);

    for (const [square, piece] of Object.entries(currentBoard)) {
      if (piece && ['K', 'Q', 'R', 'B', 'N', 'P'].includes(piece)) {
        try {
          const pieceMoves = await getLegalMoves(square);
          if (pieceMoves.length > 0) moves[square] = pieceMoves;
        } catch (e) {
          console.error(`Erreur pour ${square}:`, e);
        }
      }
    }

    setAllWhiteMoves(moves);
    setIsLoadingAllMoves(false);
  };

  const handleToggleAllMoves = async () => {
    if (!showAllMoves) {
      await loadAllWhiteMoves();
      setShowAllMoves(true);
    } else {
      setShowAllMoves(false);
      setAllWhiteMoves({});
    }
  };

  const handleGetBestMove = async () => {
    setIsLoadingBestMove(true);
    setBestMove(null);
    try {
      const move = await getBestMove();
      if (move) setBestMove(move);
    } catch (e) {
      console.error('Erreur getBestMove:', e);
    }
    setIsLoadingBestMove(false);
  };

  const handleSquareClick = async (square: string) => {
    if (isGameOver) return;

    // Autoriser la sélection + affichage des coups légaux dès que c'est le tour du joueur,
    // même si le robot n'est pas encore "idle" (déconnecté, thinking, etc.)
    // Seul l'envoi du coup (onMove) requiert que le robot soit prêt.
    const canMove = isCorrectionMode
      ? !isGameOver
      : (robotStatus === 'idle' && isWhiteTurn);

    const canSelect = isCorrectionMode || isWhiteTurn;

    const piece = board[square];

    if (selectedSquare === null) {
      if (canSelect && piece && ['K', 'Q', 'R', 'B', 'N', 'P'].includes(piece)) {
        setSelectedSquare(square);
        if (showHelpOnClick) {
          const moves = await getLegalMoves(square);
          setLegalMoves(moves);
        }
      }
    } else {
      if (square === selectedSquare) {
        setSelectedSquare(null);
        setLegalMoves([]);
      } else if (legalMoves.includes(square) || !showHelpOnClick) {
        if (canMove) {
          const success = await onMove(selectedSquare, square);
          if (success) {
            setLastMove({ from: selectedSquare, to: square });
            setBestMove(null);
            setShowAllMoves(false);
            setAllWhiteMoves({});
          }
        }
        setSelectedSquare(null);
        setLegalMoves([]);
      } else if (canSelect && piece && ['K', 'Q', 'R', 'B', 'N', 'P'].includes(piece)) {
        setSelectedSquare(square);
        if (showHelpOnClick) {
          const moves = await getLegalMoves(square);
          setLegalMoves(moves);
        }
      } else {
        setSelectedSquare(null);
        setLegalMoves([]);
      }
    }
  };

  const isLightSquare = (file: string, rank: string) => (files.indexOf(file) + ranks.indexOf(rank)) % 2 === 0;

  const hasMovesFrom = (square: string) => showAllMoves && allWhiteMoves[square]?.length > 0;
  const isDestinationFor = (square: string) => {
    if (!showAllMoves) return false;
    return Object.values(allWhiteMoves).some((moves: string[]) => moves.includes(square));
  };

  const isBestFrom = (square: string) => bestMove?.from === square;
  const isBestTo = (square: string) => bestMove?.to === square;
  const canInteract = isCorrectionMode
    ? !isGameOver
    : (isWhiteTurn && robotStatus === 'idle' && !isGameOver);

  // Cimetière : utilise cemetery_board (vision) ou pieces_eliminees (Stockfish)
  const activeCemeteryMap: { [square: string]: string } =
    showVision && cemeteryBoard && Object.keys(cemeteryBoard).length > 0
      ? cemeteryBoard
      : piecesElimineeesToMap(piecesEliminees);

  // ─── Taille unique (px) — toutes les cases font SQ×SQ ─────────────────────
  const SQ = 56;

  // Couleurs cimetière
  const CEM_BG_BLANC  = '#233040';
  const CEM_BG_NOIR   = '#1a252f';
  const CEM_BG_COIN   = '#1d2c38';
  const CEM_BORDER    = '#2d4155';

  const cemBgForSq = (sq: string): string => {
    const col = sq[0], row = sq[1];
    if ((col === '0' || col === '9') && (row === '0' || row === '9')) return CEM_BG_COIN;
    if (row === '0' || col === '0') return CEM_BG_BLANC;
    return CEM_BG_NOIR;
  };

  const renderCemCell = (sq: string) => {
    const code = activeCemeteryMap[sq];
    const pieceKey = code ? visionCodeToPieceKey(code) : null;
    return (
      <div
        key={sq}
        title={code ? `${sq}: ${code}` : sq}
        style={{
          width: SQ, height: SQ, flexShrink: 0,
          backgroundColor: cemBgForSq(sq),
          border: `1px solid ${CEM_BORDER}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          position: 'relative', boxSizing: 'border-box',
        }}
      >
        {pieceKey && PIECE_IMAGES[pieceKey] && (
          <img
            src={PIECE_IMAGES[pieceKey]}
            alt={pieceKey}
            style={{ width: SQ - 10, height: SQ - 10, pointerEvents: 'none', userSelect: 'none', opacity: 0.92 }}
            draggable={false}
          />
        )}
        <span style={{
          position: 'absolute', bottom: 2, right: 2,
          fontSize: 8, fontFamily: 'monospace', lineHeight: 1,
          color: code ? '#64748b' : '#374151', userSelect: 'none',
        }}>
          {sq}
        </span>
      </div>
    );
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-3 border border-slate-700" style={{ width: 'fit-content' }}>
      {/*
        Grille 10×10 : SQ=56px → 10×56 = 560px de côté.
        Rangée 9 (haut) = noirs capturés, rangée 0 (bas) = blancs capturés.
        Col 0 (gauche) = overflow blancs, col 9 (droite) = overflow noirs.
      */}

      {/* ── RANGÉE HAUT : [09] [a9..h9] [99] ── */}
      <div style={{ display: 'flex' }}>
        {renderCemCell('09')}
        {files.map(f => renderCemCell(`${f}9`))}
        {renderCemCell('99')}

      </div>

      {/* ── ZONE CENTRALE : [col 0] [plateau 8×8] [col 9] ── */}
      <div style={{ display: 'flex' }}>

        {/* Colonne cimetière gauche (blancs overflow : 08→01, haut→bas = rang 8→1) */}
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {ranks.map(r => renderCemCell(`0${r}`))}
        </div>

        {/* Échiquier */}
        <div
          style={{
            display: 'grid', gridTemplateColumns: `repeat(8, ${SQ}px)`,
            border: '2px solid #5c4033', borderRadius: 4,
            overflow: 'hidden', boxShadow: '0 10px 40px rgba(0,0,0,0.5)',
            position: 'relative', flexShrink: 0,
          }}
        >
          {ranks.map(rank =>
            files.map(file => {
              const square = `${file}${rank}`;
              const visionCode = showVision && visionBoard ? visionBoard[square] : null;
              const visionPieceKey = visionCode ? visionCodeToPieceKey(visionCode) : null;
              const piece = showVision && visionBoard
                ? (visionPieceKey as PieceType ?? null)
                : board[square];
              const isLight = isLightSquare(file, rank);
              const isSelected = selectedSquare === square;
              const isLegal = legalMoves.includes(square);
              const isLast = lastMove && (lastMove.from === square || lastMove.to === square);
              const hasMoves = hasMovesFrom(square);
              const isDest = isDestinationFor(square);
              const isBestF = isBestFrom(square);
              const isBestT = isBestTo(square);

              let bgColor = isLight ? '#ebecd0' : '#739552';
              if (isSelected)            bgColor = '#b9ca43';
              else if (isBestF || isBestT) bgColor = '#f7f769';
              else if (isLast)           bgColor = isLight ? '#f5f682' : '#b9ca43';
              else if (hasMoves)         bgColor = isLight ? '#e8b4e8' : '#a86da8';
              else if (isDest && !isLegal) bgColor = isLight ? '#f0d0f0' : '#c090c0';

              return (
                <div
                  key={square}
                  onClick={() => handleSquareClick(square)}
                  style={{ width: SQ, height: SQ, backgroundColor: bgColor, position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                  className={canInteract ? 'cursor-pointer transition-colors duration-100' : 'cursor-default transition-colors duration-100'}
                >
                  {isLegal && showHelpOnClick && (
                    piece
                      ? <div className="absolute inset-1 rounded-full border-[5px] border-black/60 pointer-events-none z-10" />
                      : (
                        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
                          <div className="w-[38%] h-[38%] bg-black/55 rounded-full" />
                        </div>
                      )
                  )}
                  {isBestT && !piece && (
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                      <div className="w-7 h-7 border-4 border-yellow-600 rounded-full bg-yellow-400/50" />
                    </div>
                  )}
                  {piece && PIECE_IMAGES[piece] && (
                    <img
                      src={PIECE_IMAGES[piece]} alt={piece}
                      style={{ width: SQ - 6, height: SQ - 6, pointerEvents: 'none', userSelect: 'none' }}
                      draggable={false}
                    />
                  )}
                  {isBestF && (
                    <div className="absolute top-0.5 left-0.5 bg-yellow-400 rounded-br-lg p-0.5 shadow-md">
                      <Lightbulb className="w-3 h-3 text-yellow-800" />
                    </div>
                  )}
                  {hasMoves && !isSelected && !isBestF && (
                    <div className="absolute top-0.5 right-0.5 w-3 h-3 bg-purple-600 rounded-full border border-white shadow pointer-events-none" />
                  )}
                  {/* Coordonnées */}
                  {file === 'a' && (
                    <span style={{ position: 'absolute', top: 2, left: 3, fontSize: 9, fontWeight: 700, color: isLight ? '#739552' : '#ebecd0', userSelect: 'none' }}>
                      {rank}
                    </span>
                  )}
                  {rank === '1' && (
                    <span style={{ position: 'absolute', bottom: 2, right: 3, fontSize: 9, fontWeight: 700, color: isLight ? '#739552' : '#ebecd0', userSelect: 'none' }}>
                      {file}
                    </span>
                  )}
                </div>
              );
            })
          )}

          {/* Overlays */}
          {robotStatus === 'thinking' && (
            <div className="absolute inset-0 bg-black/70 flex items-center justify-center">
              <div className="text-center text-white">
                <div className="w-12 h-12 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <div className="font-semibold text-lg">Robot réfléchit...</div>
              </div>
            </div>
          )}
          {robotStatus === 'moving' && (
            <div className="absolute inset-0 bg-black/70 flex items-center justify-center">
              <div className="text-center text-white">
                <div className="w-12 h-12 border-4 border-green-400 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <div className="font-semibold text-lg">Robot en mouvement...</div>
              </div>
            </div>
          )}
          {!isWhiteTurn && robotStatus === 'idle' && !isGameOver && (
            <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
              <div className="text-white text-xl font-semibold">🤖 Tour du robot...</div>
            </div>
          )}
          {isGameOver && (
            <div className="absolute inset-0 bg-black/80 flex items-center justify-center">
              <div className="text-center">
                <div className="text-5xl mb-2">🏆</div>
                <div className="text-white text-xl font-bold">Partie terminée</div>
              </div>
            </div>
          )}
          {robotStatus === 'disconnected' && (
            <div className="absolute inset-0 bg-black/80 flex items-center justify-center">
              <div className="text-center text-white">
                <div className="w-10 h-10 border-4 border-slate-400 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <div className="text-base">Connexion au serveur...</div>
              </div>
            </div>
          )}

          {isCorrectionMode && (
            <div className="absolute inset-0 border-4 border-amber-400 pointer-events-none rounded" />
          )}
        </div>

        {/* Colonne cimetière droite (noirs overflow : 98→91, haut→bas = rang 8→1) */}
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {ranks.map(r => renderCemCell(`9${r}`))}
        </div>
      </div>

      {/* ── RANGÉE BAS : [coin 00] [a0..h0] [coin 90] ── */}
      <div style={{ display: 'flex' }}>
        {renderCemCell('00')}
        {files.map(f => renderCemCell(`${f}0`))}
        {renderCemCell('90')}
      </div>
    </div>
  );
}
