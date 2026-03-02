import { useState } from 'react';
import { motion } from 'motion/react';
import { Star, Send, Home, MessageSquare } from 'lucide-react';

interface FeedbackScreenProps {
  onReturnToMenu: () => void;
  playerName: string;
  difficulty: string;
  result: 'win' | 'lose' | 'draw' | 'abandoned';
  acplScore: number;
}

export function FeedbackScreen({ 
  onReturnToMenu, 
  playerName, 
  difficulty,
  result,
  acplScore 
}: FeedbackScreenProps) {
  const [rating, setRating] = useState(0);
  const [hoveredRating, setHoveredRating] = useState(0);
  const [comment, setComment] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async () => {
    // Envoi du feedback à l'API
    try {
      await fetch(`http://${window.location.hostname}:8000/feedback/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          player_name: playerName,
          rating,
          comment,
          difficulty,
          result,
          acpl_score: acplScore,
          timestamp: new Date().toISOString(),
        }),
      });
    } catch {
      // Fallback localStorage si API indisponible
      const feedbackData = localStorage.getItem('chessFeedback');
      const feedback = feedbackData ? JSON.parse(feedbackData) : [];
      feedback.push({
        playerName, rating, comment, difficulty, result, acplScore,
        timestamp: new Date().toISOString(),
      });
      localStorage.setItem('chessFeedback', JSON.stringify(feedback));
    }
    
    setSubmitted(true);
  };

  const resultLabels = {
    win: 'Victoire',
    lose: 'Défaite',
    draw: 'Match nul',
    abandoned: 'Partie arrêtée'
  };

  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="max-w-md w-full bg-slate-800/50 backdrop-blur-xl rounded-3xl border border-slate-700 shadow-2xl p-8 text-center"
        >
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring', damping: 10 }}
            className="mb-6"
          >
            <div className="w-20 h-20 mx-auto bg-green-500/20 rounded-full flex items-center justify-center border-2 border-green-500/50">
              <Send className="w-10 h-10 text-green-400" />
            </div>
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="text-3xl font-bold text-white mb-3"
          >
            Merci pour votre feedback !
          </motion.h2>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="text-slate-300 mb-8"
          >
            Vos retours nous aident à améliorer l'expérience de jeu avec le robot UR7e.
          </motion.p>

          <motion.button
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            onClick={onReturnToMenu}
            className="
              w-full px-6 py-4 rounded-xl font-bold text-lg
              bg-gradient-to-r from-cyan-500 to-blue-600
              hover:from-cyan-400 hover:to-blue-500
              text-white shadow-lg shadow-cyan-500/30
              hover:shadow-cyan-400/50 hover:scale-105
              transition-all duration-300
              flex items-center justify-center gap-2
            "
          >
            <Home className="w-5 h-5" />
            Retour au menu
          </motion.button>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-2xl w-full bg-slate-800/50 backdrop-blur-xl rounded-3xl border border-slate-700 shadow-2xl p-8"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', damping: 10 }}
            className="inline-block mb-4"
          >
            <div className="w-16 h-16 mx-auto bg-cyan-500/20 rounded-full flex items-center justify-center border-2 border-cyan-500/50">
              <MessageSquare className="w-8 h-8 text-cyan-400" />
            </div>
          </motion.div>

          <h1 className="text-4xl font-bold text-white mb-2">
            Votre avis compte !
          </h1>
          <p className="text-slate-300 text-lg">
            Comment s'est passée votre partie contre le robot UR7e ?
          </p>
        </div>

        {/* Game Summary */}
        <div className="bg-slate-700/30 rounded-xl p-4 mb-8 border border-slate-600/50">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-slate-400">Joueur:</span>
              <span className="text-white font-semibold ml-2">{playerName}</span>
            </div>
            <div>
              <span className="text-slate-400">Difficulté:</span>
              <span className="text-cyan-400 font-semibold ml-2">
                {difficulty === 'beginner' ? 'Débutant' : difficulty === 'intermediate' ? 'Intermédiaire' : 'Difficile'}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Résultat:</span>
              <span className="text-white font-semibold ml-2">{resultLabels[result]}</span>
            </div>
            <div>
              <span className="text-slate-400">Score ACPL:</span>
              <span className="text-cyan-400 font-semibold ml-2">{acplScore}</span>
            </div>
          </div>
        </div>

        {/* Rating */}
        <div className="mb-8">
          <label className="block text-white font-semibold mb-4 text-lg">
            Notez votre expérience
          </label>
          <div className="flex items-center justify-center gap-3">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                onClick={() => setRating(star)}
                onMouseEnter={() => setHoveredRating(star)}
                onMouseLeave={() => setHoveredRating(0)}
                className="transition-all duration-200 hover:scale-125"
              >
                <Star
                  className={`w-12 h-12 transition-colors ${
                    star <= (hoveredRating || rating)
                      ? 'text-yellow-400 fill-yellow-400'
                      : 'text-slate-600'
                  }`}
                />
              </button>
            ))}
          </div>
          {rating > 0 && (
            <p className="text-center text-slate-400 mt-3">
              {rating === 1 && 'Très décevant'}
              {rating === 2 && 'Décevant'}
              {rating === 3 && 'Correct'}
              {rating === 4 && 'Très bien'}
              {rating === 5 && 'Excellent !'}
            </p>
          )}
        </div>

        {/* Comment */}
        <div className="mb-8">
          <label className="block text-white font-semibold mb-3 text-lg">
            Commentaire (optionnel)
          </label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Partagez votre expérience, suggestions d'amélioration..."
            className="
              w-full bg-slate-700/50 border border-slate-600 rounded-xl
              text-white placeholder-slate-500
              px-4 py-3 min-h-[120px] resize-none
              focus:outline-none focus:ring-2 focus:ring-cyan-500/50
              transition-all
            "
            maxLength={500}
          />
          <div className="text-right text-slate-500 text-sm mt-2">
            {comment.length}/500
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4">
          <button
            onClick={onReturnToMenu}
            className="
              flex-1 px-6 py-4 rounded-xl font-bold text-lg
              bg-slate-700 hover:bg-slate-600
              text-white
              transition-all duration-300
              hover:scale-105
            "
          >
            Passer
          </button>
          <button
            onClick={handleSubmit}
            disabled={rating === 0}
            className={`
              flex-1 px-6 py-4 rounded-xl font-bold text-lg
              ${rating === 0
                ? 'bg-slate-700/50 text-slate-500 cursor-not-allowed'
                : 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 shadow-lg shadow-cyan-500/30 hover:shadow-cyan-400/50 hover:scale-105'
              }
              text-white
              transition-all duration-300
              flex items-center justify-center gap-2
            `}
          >
            <Send className="w-5 h-5" />
            Envoyer
          </button>
        </div>
      </motion.div>
    </div>
  );
}
