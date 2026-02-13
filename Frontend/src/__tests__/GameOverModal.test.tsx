import { render, screen } from '@testing-library/react';
import { GameOverModal } from '../components/GameOverModal';

describe('GameOverModal', () => {
  it('affiche le bouton retour au menu', () => {
    render(
      <GameOverModal
        isVisible={true}
        result="white"
        acplScore={10}
        totalMoves={20}
        elapsedTime={120}
        playerName="Test"
        onReturnToMenu={() => {}}
        onViewLeaderboard={() => {}}
      />
    );
    expect(screen.getByText(/retour au menu/i)).toBeInTheDocument();
  });
});
