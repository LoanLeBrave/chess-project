import { useState } from 'react';
import { AlertTriangle, Hand, ShieldAlert, CircleStop, CheckCircle, ArrowLeft } from 'lucide-react';
import { Button } from './ui/button';
import { Checkbox } from './ui/checkbox';
import { Card } from './ui/card';
import { Alert, AlertDescription, AlertTitle } from './ui/alert';

interface SafetyScreenProps {
  onContinue: () => void;
  onBack: () => void;
}

export function SafetyScreen({ onContinue, onBack }: SafetyScreenProps) {
  const [hasAccepted, setHasAccepted] = useState(false);

  const safetyRules = [
    {
      icon: Hand,
      title: "Zone d'exclusion",
      description: "Ne jamais placer vos mains sur l'échiquier lorsque le bras est en mouvement.",
      color: "from-red-500 to-orange-500",
      iconBg: "bg-red-500/10",
      iconColor: "text-red-500"
    },
    {
      icon: ShieldAlert,
      title: "Interférence",
      description: "Merci de ne pas empêcher le robot de jouer ou de bloquer sa trajectoire.",
      color: "from-orange-500 to-yellow-500",
      iconBg: "bg-orange-500/10",
      iconColor: "text-orange-500"
    },
    {
      icon: CircleStop,
      title: "Arrêt d'urgence",
      description: "Repérez le bouton d'arrêt d'urgence physique avant de commencer.",
      color: "from-yellow-500 to-amber-500",
      iconBg: "bg-yellow-500/10",
      iconColor: "text-yellow-500"
    }
  ];

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      {/* Back Button */}
      <button
        onClick={onBack}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onBack(); }}
        className="absolute top-6 left-6 flex items-center gap-2 text-slate-400 hover:text-white transition-colors group"
      >
        <div className="w-10 h-10 rounded-full bg-slate-800/50 border border-slate-700 flex items-center justify-center group-hover:border-cyan-400 transition-all">
          <ArrowLeft className="w-5 h-5" />
        </div>
        <span className="font-medium">Retour</span>
      </button>

      <div className="max-w-4xl w-full">
        {/* Titre */}
        <div className="text-center mb-10">
          <div className="flex items-center justify-center gap-3 mb-4">
            <AlertTriangle className="w-12 h-12 text-yellow-500" strokeWidth={2} />
            <h1 className="text-5xl font-bold text-white">
              Consignes de Sécurité
            </h1>
          </div>
          <p className="text-xl text-slate-400">
            Veuillez lire attentivement les consignes avant de continuer
          </p>
        </div>

        {/* Vidéo de démonstration */}
        <Card className="mb-8 bg-slate-800/50 border-slate-700 overflow-hidden">
          <div className="relative aspect-video bg-slate-900/80 flex items-center justify-center">
            {/* Placeholder pour la vidéo */}
            <div className="text-center p-8">
              <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-slate-700/50 flex items-center justify-center">
                <svg className="w-10 h-10 text-slate-500" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                </svg>
              </div>
              <p className="text-slate-400 text-lg">
                Vidéo de démonstration du robot UR7e
              </p>
              <p className="text-slate-500 text-sm mt-2">
                La vidéo sera disponible prochainement
              </p>
            </div>
          </div>
        </Card>

        {/* Cartes d'avertissement */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {safetyRules.map((rule, index) => {
            const Icon = rule.icon;
            return (
              <Card 
                key={index}
                className="p-6 bg-slate-800/50 border-slate-700 hover:border-slate-600 transition-all duration-300"
              >
                <div className={`w-14 h-14 rounded-xl ${rule.iconBg} flex items-center justify-center mb-4`}>
                  <Icon className={`w-7 h-7 ${rule.iconColor}`} strokeWidth={2} />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">{rule.title}</h3>
                <p className="text-slate-400 leading-relaxed">{rule.description}</p>
              </Card>
            );
          })}
        </div>

        {/* Engagement */}
        <Alert className="mb-8 bg-slate-800/50 border-slate-600">
          <AlertTriangle className="h-5 w-5 text-yellow-500" />
          <AlertTitle className="text-white text-lg">Important</AlertTitle>
          <AlertDescription className="text-slate-300">
            Votre sécurité est notre priorité. En cochant la case ci-dessous, vous reconnaissez avoir pris connaissance des consignes et vous engagez à les respecter pendant toute la durée de votre partie.
          </AlertDescription>
        </Alert>

        {/* Case à cocher */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 mb-8">
          <div className="flex items-start gap-4">
            <Checkbox 
              id="safety-agreement"
              checked={hasAccepted}
              onCheckedChange={(checked) => setHasAccepted(checked === true)}
              className="mt-1 data-[state=checked]:bg-cyan-500 data-[state=checked]:border-cyan-500"
            />
            <label 
              htmlFor="safety-agreement" 
              className="text-lg text-slate-200 cursor-pointer select-none flex-1"
            >
              J'ai lu les consignes de sécurité et je m'engage à les respecter pendant toute la durée de ma partie avec le robot UR7e.
            </label>
          </div>
        </div>

        {/* Bouton Continuer */}
        <div className="flex justify-center">
          <Button
            onClick={onContinue}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onContinue(); }}
            disabled={!hasAccepted}
            size="lg"
            className={`
              px-12 py-6 rounded-2xl text-xl font-bold
              transition-all duration-300
              ${hasAccepted 
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-2xl shadow-cyan-500/50 hover:shadow-cyan-400/60 hover:scale-105' 
                : 'bg-slate-700 text-slate-500 cursor-not-allowed'
              }
              border-0
            `}
          >
            {hasAccepted ? (
              <>
                <CheckCircle className="w-5 h-5 mr-2" />
                Continuer
              </>
            ) : (
              'Veuillez accepter les consignes'
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
