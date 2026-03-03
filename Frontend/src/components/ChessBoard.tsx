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
  showVision, visionBoard, visionConfidence,
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
    if (isGameOver || robotStatus !== 'idle' || !isWhiteTurn) return;

    const piece = board[square];

    if (selectedSquare === null) {
      if (piece && ['K', 'Q', 'R', 'B', 'N', 'P'].includes(piece)) {
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
        const success = await onMove(selectedSquare, square);
        if (success) {
          setLastMove({ from: selectedSquare, to: square });
          setBestMove(null);
          setShowAllMoves(false);
          setAllWhiteMoves({});
        }
        setSelectedSquare(null);
        setLegalMoves([]);
      } else if (piece && ['K', 'Q', 'R', 'B', 'N', 'P'].includes(piece)) {
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
  const canInteract = isWhiteTurn && robotStatus === 'idle' && !isGameOver;

  // Cimetière : utilise cemetery_board (vision) ou pieces_eliminees (Stockfish)
  const activeCemeteryMap: { [square: string]: string } =
    showVision && cemeteryBoard && Object.keys(cemeteryBoard).length > 0
      ? cemeteryBoard
      : piecesElimineeesToMap(piecesEliminees);

  /**
   * Cases blancs capturés : rang 0 (a0-h0), coins 00/90, col gauche 01-08
   * Cases noirs capturés  : rang 9 (a9-h9), coins 09/99, col droite 91-98
   */
  const isBlancsCell = (sq: string) => sq[0] === '0' || sq[1] === '0';
  const cemBg = (sq: string) => isBlancsCell(sq) ? '#2a3a4a' : '#1a2a3a';
  const cemBorder = (sq: string) => isBlancsCell(sq) ? '#3b5268' : '#243447';

  /**
   * Cellule de cimetière générique.
   * - widthClass / heightClass : classes Tailwind w-* h-*
   * - rankLabel : si fourni, affiche le numéro de rang en petit label
   */
  const renderCemCell = (sq: string, widthClass: string, heightClass: string, rankLabel?: string) => {
    const code = activeCemeteryMap[sq];
    const pieceKey = code ? visionCodeToPieceKey(code) : null;
    return (
      <div
        key={sq}
        className={`${widthClass} ${heightClass} flex items-center justify-center relative flex-shrink-0`}
        style={{ backgroundColor: cemBg(sq), border: `1px solid ${cemBorder(sq)}` }}
        title={code ? `${sq}: ${code}` : sq}
      >
        {pieceKey && PIECE_IMAGES[pieceKey] && (
          <img
            src={PIECE_IMAGES[pieceKey]}
            alt={pieceKey}
            className="w-9 h-9 pointer-events-none select-none opacity-90"
            draggable={false}
          />
        )}
        {/* Étiquette de la case (toujours visible en coin) */}
        <span
          className="absolute bottom-0.5 right-0.5 text-[8px] font-mono leading-none select-none"
          style={{ color: code ? '#94a3b8' : '#4b5563' }}
        >
          {rankLabel ?? sq}
        </span>
      </div>
    );
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700">
      <div className="inline-block">

        {/* ═══════════════════════════════════════════════════════════════
            BANDE HAUT : coins 09/99 + rangée 9 (noirs capturés)
            Largeur : w-11(coin) + 8×w-16(plateau) + w-11(coin) = 44+512+44 = 600px
            ═══════════════════════════════════════════════════════════════ */}
        <div className="flex mb-0.5">
          {renderCemCell('09', 'w-11', 'h-11')}
          {files.map(f => renderCemCell(`${f}9`, 'w-16', 'h-11'))}
          {renderCemCell('99', 'w-11', 'h-11')}
        </div>

        {/* Lettres haut — décalées de w-11=44px pour s'aligner sur le plateau */}
        <div className="flex" style={{ marginLeft: '44px' }}>
          {files.map(f => (
            <div key={f} className="w-16 text-center text-slate-400 text-sm font-bold">{f}</div>
          ))}
        </div>

        {/* ═══════════════════════════════════════════════════════════════
            ZONE CENTRALE : col gauche (blancs overflow) + plateau + col droite (noirs overflow)
            Col gauche  : cases 01-08 (blancs capturés en excès)
            Col droite  : cases 91-98 (noirs capturés en excès)
            Les labels sont les numéros de rang 1-8 du plateau
            ═══════════════════════════════════════════════════════════════ */}
        <div className="flex">

          {/* Colonne cimetière gauche : blancs overflow (01..08, de haut en bas = rang 8..1) */}
          <div className="flex flex-col">
            {ranks.map(r => renderCemCell(`0${r}`, 'w-11', 'h-16', r))}
          </div>

          {/* Échiquier */}
          <div className="grid grid-cols-8 rounded-md overflow-hidden shadow-2xl relative" style={{ border: '3px solid #5c4033' }}>
            {ranks.map(rank =>
              files.map(file => {
                const square = `${file}${rank}`;
                // En mode vision : afficher les pieces detectees par la camera
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

                // Couleurs style chess.com
                let bgColor = isLight ? '#ebecd0' : '#739552';
                if (isSelected) {
                  bgColor = '#b9ca43';
                } else if (isBestF || isBestT) {
                  bgColor = '#f7f769';
                } else if (isLast) {
                  bgColor = isLight ? '#f5f682' : '#b9ca43';
                } else if (hasMoves) {
                  bgColor = isLight ? '#e8b4e8' : '#a86da8';
                } else if (isDest && !isLegal) {
                  bgColor = isLight ? '#f0d0f0' : '#c090c0';
                }

                return (
                  <div
                    key={square}
                    onClick={() => handleSquareClick(square)}
                    className={`w-16 h-16 flex items-center justify-center relative
                      ${canInteract ? 'cursor-pointer' : 'cursor-default'}
                      transition-colors duration-100`}
                    style={{ backgroundColor: bgColor }}
                  >
                    {/* Indicateur coup légal - point ou cercle */}
                    {isLegal && showHelpOnClick && (
                      piece ? (
                        <div className="absolute inset-1 rounded-full border-[5px] border-black/40 pointer-events-none" />
                      ) : (
                        <div className="absolute w-[30%] h-[30%] bg-black/30 rounded-full pointer-events-none" />
                      )
                    )}

                    {/* Indicateur meilleur coup destination */}
                    {isBestT && !piece && (
                      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                        <div className="w-8 h-8 border-4 border-yellow-600 rounded-full bg-yellow-400/50" />
                      </div>
                    )}

                    {/* Pièce */}
                    {piece && PIECE_IMAGES[piece] && (
                      <img
                        src={PIECE_IMAGES[piece]}
                        alt={piece}
                        className="w-14 h-14 pointer-events-none select-none"
                        draggable={false}
                      />
                    )}

                    {/* Icône meilleur coup départ */}
                    {isBestF && (
                      <div className="absolute top-0.5 left-0.5 bg-yellow-400 rounded-br-lg p-1 shadow-md">
                        <Lightbulb className="w-4 h-4 text-yellow-800" />
                      </div>
                    )}

                    {/* Badge pièce jouable */}
                    {hasMoves && !isSelected && !isBestF && (
                      <div className="absolute top-1 right-1 w-4 h-4 bg-purple-600 rounded-full border-2 border-white shadow pointer-events-none" />
                    )}

                    {/* Coordonnées dans les coins */}
                    {file === 'a' && (
                      <span className={`absolute top-0.5 left-1 text-xs font-bold ${isLight ? 'text-[#739552]' : 'text-[#ebecd0]'}`}>
                        {rank}
                      </span>
                    )}
                    {rank === '1' && (
                      <span className={`absolute bottom-0.5 right-1 text-xs font-bold ${isLight ? 'text-[#739552]' : 'text-[#ebecd0]'}`}>
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
                  <div className="w-16 h-16 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                  <div className="font-semibold text-xl">Robot réfléchit...</div>
                </div>
              </div>
            )}
            {robotStatus === 'moving' && (
              <div className="absolute inset-0 bg-black/70 flex items-center justify-center">
                <div className="text-center text-white">
                  <div className="w-16 h-16 border-4 border-green-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                  <div className="font-semibold text-xl">Robot en mouvement...</div>
                </div>
              </div>
            )}
            {!isWhiteTurn && robotStatus === 'idle' && !isGameOver && (
              <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                <div className="text-white text-2xl font-semibold">🤖 Tour du robot...</div>
              </div>
            )}
            {isGameOver && (
              <div className="absolute inset-0 bg-black/80 flex items-center justify-center">
                <div className="text-center">
                  <div className="text-6xl mb-3">🏆</div>
                  <div className="text-white text-2xl font-bold">Partie terminée</div>
                </div>
              </div>
            )}
            {robotStatus === 'disconnected' && (
              <div className="absolute inset-0 bg-black/80 flex items-center justify-center">
                <div className="text-center text-white">
                  <div className="w-12 h-12 border-4 border-slate-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                  <div className="text-lg">Connexion au serveur...</div>
                </div>
              </div>
            )}
          </div>

          {/* Colonne cimetière droite : noirs overflow (91..98, de haut en bas = rang 8..1) */}
          <div className="flex flex-col">
            {ranks.map(r => renderCemCell(`9${r}`, 'w-11', 'h-16', r))}
          </div>
        </div>

        {/* Lettres bas — même décalage w-11 */}
        <div className="flex" style={{ marginLeft: '44px' }}>
          {files.map(f => (
            <div key={f} className="w-16 text-center text-slate-400 text-sm font-bold">{f}</div>
          ))}
        </div>

        {/* ═══════════════════════════════════════════════════════════════
            BANDE BAS : coins 00/90 + rangée 0 (blancs capturés)
            ═══════════════════════════════════════════════════════════════ */}
        <div className="flex mt-0.5">
          {renderCemCell('00', 'w-11', 'h-11')}
          {files.map(f => renderCemCell(`${f}0`, 'w-16', 'h-11'))}
          {renderCemCell('90', 'w-11', 'h-11')}
        </div>

      </div>
    </div>
  );
}
