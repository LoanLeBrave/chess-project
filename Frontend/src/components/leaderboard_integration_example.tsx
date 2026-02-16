
/**
 * Fonction à appeler en fin de partie pour calculer l'ACPL et enregistrer le score
 */
async function saveGameToLeaderboard(
  playerName: string,
  result: 'win' | 'lose' | 'abandoned',
  difficulty: string,
  gameStartTime: Date
) {
  try {
    // 1. Récupérer l'historique des coups
    const historyResponse = await fetch('http://localhost:8000/game/history');
    const historyData = await historyResponse.json();
    
    const movesPlayed = historyData.move_count;
    
    // 2. Calculer la durée de la partie (en secondes)
    const gameDuration = (Date.now() - gameStartTime.getTime()) / 1000;

    
    const acpl = await calculateACPL(historyData.moves);
    
    // 4. Enregistrer dans le leaderboard
    const response = await fetch('http://localhost:8000/leaderboard/add-game', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        player_name: playerName,
        acpl: acpl,
        result: result,
        difficulty: difficulty,
        moves_played: movesPlayed,
        game_duration: gameDuration
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      console.log('✅ Score enregistré dans le leaderboard');
      return true;
    } else {
      console.error('❌ Erreur:', data.error);
      return false;
    }
    
  } catch (error) {
    console.error('❌ Erreur lors de l\'enregistrement:', error);
    return false;
  }
}

/**
 * Calcul de l'ACPL (Average Centipawn Loss)
 * Cette fonction doit être adaptée selon comment vous stockez les évaluations
 */
async function calculateACPL(moves: any[]): Promise<number> {

  let totalLoss = 0;
  let playerMoves = 0;
  
  // Supposons que vous avez stocké les évaluations dans votre state
  const evaluations = getStoredEvaluations(); // À implémenter
  
  for (let i = 0; i < evaluations.length; i++) {
    if (i === 0) continue; // Ignorer la position initiale
    
    const prevEval = evaluations[i - 1];
    const currEval = evaluations[i];
    
    // Si c'est un coup du joueur (pas du robot)
    if (i % 2 === 1) { // Adapter selon qui joue en premier
      const loss = Math.abs(currEval - prevEval);
      totalLoss += loss;
      playerMoves++;
    }
  }
  
  const acpl = playerMoves > 0 ? totalLoss / playerMoves : 0;
  return Math.round(acpl * 100) / 100; // Arrondir à 2 décimales
}

/**
 * Fonction utilitaire pour récupérer les évaluations stockées
 * À implémenter selon votre architecture
 */
function getStoredEvaluations(): number[] {
  // Exemple: récupérer depuis un state React
  
  return []; // Placeholder
}

export { saveGameToLeaderboard, calculateACPL };
