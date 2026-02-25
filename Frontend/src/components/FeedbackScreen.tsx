import { useState } from 'react';
import { Star, Send, ArrowLeft, CheckCircle } from 'lucide-react';
import { Button } from './ui/button';
import { Card } from './ui/card';

interface FeedbackScreenProps {
  onSubmit: (ratings: RatingData, comment: string) => void;
  onBack: () => void;
  playerName: string;
}

interface RatingData {
  overall: number;
  design: number;
  gameplay: number;
  robotLevel: number;
}

export function FeedbackScreen({ onSubmit, onBack, playerName }: FeedbackScreenProps) {
  const [ratings, setRatings] = useState<RatingData>({
    overall: 0,
    design: 0,
    gameplay: 0,
    robotLevel: 0,
  });
  const [hoveredRatings, setHoveredRatings] = useState<RatingData>({
    overall: 0,
    design: 0,
    gameplay: 0,
    robotLevel: 0,
  });
  
  const [comment, setComment] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = async () => {
    if (ratings.overall > 0) {
      const feedbackData = {
        playerName,
        ratings,
        comment,
        timestamp: new Date().toISOString(),
      };

      try {
        await fetch('http://10.33.14.216:3001/feedback', { 
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(feedbackData),
        });

        setIsSubmitted(true);

        setTimeout(() => {
          onSubmit(ratings, comment);
        }, 2000);

      } catch (error) {
        console.error('Erreur envoi feedback:', error);
      }

    } else {
      onSubmit(ratings, '');
    }
  };

  const handleRatingChange = (category: keyof RatingData, value: number) => {
    setRatings(prev => ({ ...prev, [category]: value }));
  };

  const handleHoverChange = (category: keyof RatingData, value: number) => {
    setHoveredRatings(prev => ({ ...prev, [category]: value }));
  };

  const renderStars = (category: keyof RatingData, size: 'large' | 'small' = 'small') => {
    const starSize = size === 'large' ? 'w-14 h-14' : 'w-8 h-8';
    
    return [1, 2, 3, 4, 5].map((star) => {
      const isFilled = star <= (hoveredRatings[category] || ratings[category]);
      return (
        <button
          key={star}
          onClick={() => handleRatingChange(category, star)}
          onMouseEnter={() => handleHoverChange(category, star)}
          onMouseLeave={() => handleHoverChange(category, 0)}
          className="transition-all duration-200 hover:scale-110"
        >
          <Star
            className={`${starSize} transition-all duration-200 ${
              isFilled
                ? 'fill-yellow-400 text-yellow-400 drop-shadow-[0_0_8px_rgba(250,204,21,0.5)]'
                : 'text-slate-600 hover:text-slate-500'
            }`}
            strokeWidth={2}
          />
        </button>
      );
    });
  };

  const getRatingText = (rating: number) => {
    if (rating === 0) return '';
    if (rating === 1) return 'Très insatisfait';
    if (rating === 2) return 'Insatisfait';
    if (rating === 3) return 'Neutre';
    if (rating === 4) return 'Satisfait';
    return 'Très satisfait';
  };

  const getCommentPlaceholder = () => {
    if (ratings.overall <= 2) return 'Dites-nous ce qui pourrait être amélioré...';
    if (ratings.overall === 3) return 'Partagez votre expérience...';
    return 'Qu\'avez-vous particulièrement apprécié ?';
  };

  const categories = [
    { key: 'design' as keyof RatingData, label: 'Design de l\'interface', icon: '🎨' },
    { key: 'gameplay' as keyof RatingData, label: 'Expérience de jeu', icon: '♟️' },
    { key: 'robotLevel' as keyof RatingData, label: 'Niveau du robot', icon: '🤖' },
  ];

  if (isSubmitted) {
    return (
      <div className="h-screen flex items-center justify-center p-4">
        <Card className="p-8 bg-slate-800/50 border-slate-700 text-center max-w-md">
          <div className="mb-4 flex justify-center">
            <div className="w-20 h-20 rounded-full bg-green-500/20 flex items-center justify-center">
              <CheckCircle className="w-12 h-12 text-green-500" />
            </div>
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">
            Merci pour votre avis !
          </h2>
          <p className="text-slate-400">
            Votre retour nous aide à améliorer l'expérience
          </p>
          <div className="mt-6 flex justify-center gap-1">
            {[...Array(ratings.overall)].map((_, i) => (
              <Star
                key={i}
                className="w-8 h-8 fill-yellow-400 text-yellow-400"
              />
            ))}
          </div>
          {comment && (
            <div className="mt-4 p-4 bg-slate-900/50 rounded-lg">
              <p className="text-sm text-slate-300 italic">"{comment}"</p>
            </div>
          )}
        </Card>
      </div>
    );
  }

  return (
    <div className="h-screen flex items-center justify-center p-6 overflow-auto">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="fixed top-4 left-4 flex items-center gap-2 text-slate-400 hover:text-white transition-colors group z-10"
      >
        <div className="w-9 h-9 rounded-full bg-slate-800/50 border border-slate-700 flex items-center justify-center group-hover:border-cyan-400 transition-all">
          <ArrowLeft className="w-4 h-4" />
        </div>
        <span className="font-medium text-sm">Retour</span>
      </button>

      {/* Skip Button */}
      <button
        onClick={() => onSubmit(ratings, '')}
        className="fixed top-4 right-4 text-slate-400 hover:text-white transition-colors group z-10"
      >
        <span className="font-medium text-sm underline">Passer</span>
      </button>

      <div className="max-w-3xl w-full py-6">
        {/* Titre */}
        <div className="text-center mb-5">
          <h1 className="text-3xl font-bold text-white mb-2">
            Votre Avis Nous Intéresse
          </h1>
          <p className="text-slate-400">
            Comment s'est passée votre partie contre le robot UR7e ?
          </p>
        </div>

        <Card className="p-5 bg-slate-800/50 border-slate-700">
          {/* Note générale */}
          <div className="mb-6">
            <h2 className="text-xl font-bold text-white mb-3 text-center">
              ⭐ Note générale
            </h2>
            <div className="flex justify-center gap-2 mb-2">
              {renderStars('overall', 'large')}
            </div>
            {ratings.overall > 0 && (
              <p className="text-center text-base font-medium text-cyan-400 transition-all duration-300">
                {getRatingText(ratings.overall)}
              </p>
            )}
          </div>

          {/* Notes détaillées */}
          <div className="space-y-3 mb-5">
            <h3 className="text-base font-semibold text-white mb-2">
              Notez en détail
            </h3>
            
            {categories.map((category) => (
              <div key={category.key} className="flex items-center gap-3">
                <div className="flex items-center gap-2 min-w-[160px]">
                  <span className="text-xl">{category.icon}</span>
                  <span className="text-sm font-medium text-slate-300">
                    {category.label}
                  </span>
                </div>
                <div className="flex gap-1 flex-1 justify-center">
                  {renderStars(category.key, 'small')}
                </div>
              </div>
            ))}
          </div>

          {/* Zone de commentaire */}
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Votre commentaire (optionnel)
              </label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder={getCommentPlaceholder()}
                rows={3}
                maxLength={500}
                className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 transition-all resize-none"
              />
              <p className="text-xs text-slate-500 mt-1">
                {comment.length} / 500 caractères
              </p>
            </div>

            {/* Bouton d'envoi */}
            <div className="flex justify-center pt-1">
              <Button
                onClick={handleSubmit}
                size="lg"
                disabled={ratings.overall === 0}
                className="px-8 py-5 rounded-xl text-base font-bold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-2xl shadow-cyan-500/50 hover:shadow-cyan-400/60 hover:scale-105 transition-all duration-300 border-0 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
              >
                <Send className="w-4 h-4 mr-2" />
                Envoyer mon avis
              </Button>
            </div>
          </div>
        </Card>

        {/* Info sur qui reçoit l'avis */}
        <div className="mt-4 text-center">
          <p className="text-xs text-slate-500">
            Votre avis sera transmis à l'équipe de développement pour améliorer l'expérience
          </p>
        </div>
      </div>
    </div>
  );
}
