import { render, screen } from '@testing-library/react';
import { ChessBoard } from '../components/ChessBoard';

describe('ChessBoard', () => {
  it('affiche l’échiquier', () => {
    render(
      <ChessBoard
        board={Array(8).fill(Array(8).fill(null))}
        selectedSquare={null}
        onSquareClick={() => {}}
        legalMoves={[]}
        lastMove={null}
        robotStatus={null}
        showHints={false}
        showLegalMoves={false}
        isPlayerTurn={true}
        isFlipped={false}
      />
    );
    expect(screen.getByTestId('chess-board')).toBeInTheDocument();
  });
});
