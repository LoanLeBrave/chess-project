import { render, screen } from '@testing-library/react';
import { SafetyScreen } from '../components/SafetyScreen';

describe('SafetyScreen', () => {
  it('affiche les règles de sécurité', () => {
    render(<SafetyScreen onContinue={() => {}} onBack={() => {}} />);
    expect(screen.getByText(/zone d'exclusion/i)).toBeInTheDocument();
    expect(screen.getByText(/interférence/i)).toBeInTheDocument();
    expect(screen.getByText(/arrêt d'urgence/i)).toBeInTheDocument();
  });
});
