---
id: robot-routes
title: Routes robot
sidebar_position: 4
---

# Routes robot

## `POST /robot/connect`

Établit la connexion RTDE avec le robot.

**Corps :** aucun

**Réponse :**
```json
{
  "status": "ok",
  "message": "Robot connecté",
  "ip": "192.168.1.100"
}
```

**Erreur :**
```json
{
  "status": "error",
  "message": "Impossible de se connecter au robot après 8 tentatives"
}
```

---

## `POST /robot/disconnect`

Ferme proprement la connexion RTDE.

**Corps :** aucun

---

## `POST /robot/freedrive`

Active ou désactive le mode FreeDrive (guidage manuel).

**Corps :**
```json
{"enable": true}
```

**Réponse :**
```json
{
  "status": "ok",
  "freedrive": true
}
```

:::warning
En FreeDrive, les boutons de mouvement Z dans l'interface sont automatiquement désactivés.
:::

---

## `POST /robot/move-z`

Déplace l'axe Z d'un step (pour la calibration).

**Corps :**
```json
{
  "direction": "up",
  "step": 5
}
```

| Paramètre | Valeurs | Description |
|-----------|---------|-------------|
| `direction` | `"up"`, `"down"` | Sens du mouvement |
| `step` | entier (mm) | Amplitude du mouvement |

---

## `GET /robot/position`

Lit la position TCP actuelle du robot.

**Réponse :**
```json
{
  "x": 0.412,
  "y": -0.231,
  "z": -0.089,
  "rx": 3.14,
  "ry": 0.0,
  "rz": 0.0
}
```

---

## `POST /robot/save-calibration`

Sauvegarde les paramètres de calibration.

**Corps :**
```json
{
  "board_origin": [0.412, -0.231, -0.089, 3.14, 0.0, 0.0],
  "case_size": 0.055,
  "z_approach": -0.080,
  "z_depose": -0.150
}
```

**Réponse :**
```json
{
  "status": "ok",
  "message": "Calibration sauvegardée"
}
```

---

## `GET /robot/status`

Retourne l'état de connexion du robot.

**Réponse :**
```json
{
  "connected": true,
  "is_paused": false,
  "mode": "running"
}
```
