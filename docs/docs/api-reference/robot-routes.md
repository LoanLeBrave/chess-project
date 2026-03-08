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

## `POST /robot/calibrate/freedrive`

Active ou désactive le mode FreeDrive (guidage manuel) pendant la calibration.

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
En FreeDrive, les boutons de mouvement Z dans l'interface sont automatiquement désactivés pour éviter les conflits de commande.
:::

---

## `POST /robot/calibrate/auto-level`

Verticalise la pince et la ferme pour qu'elle puisse entrer dans les trous de calibration. Appelé automatiquement après la saisie du PIN.

**Corps :** aucun

---

## `POST /robot/calibrate/point`

Enregistre la position TCP actuelle comme point de calibration.

**Corps :**
```json
{
  "point": "a1",
  "freedrive_active": true
}
```

| Paramètre | Valeurs | Description |
|-----------|---------|-------------|
| `point` | `"a1"`, `"h8"`, `"z"` | Point à enregistrer |
| `freedrive_active` | booléen | Si true, le FreeDrive est réactivé après la montée de sécurité |

Après enregistrement de `a1` ou `h8`, le robot **remonte de 10 cm** automatiquement.

---

## `POST /robot/calibrate/save`

Calcule la géométrie de l'échiquier à partir des points A1, H8 et Z enregistrés, puis sauvegarde dans `robot_calibration.json`.

**Corps :** aucun

**Réponse :**
```json
{
  "status": "ok",
  "message": "Calibration sauvegardée (rotation=X.XXdeg)",
  "origin": [-0.0416, 0.4695, 0.1454],
  "rotation": 3.1652,
  "board_size": 0.2686
}
```

---

## `POST /robot/calibrate/move-z/start`

Démarre un déplacement Z continu (maintenir le bouton appuyé dans l'interface).

**Corps :**
```json
{
  "direction": "down",
  "velocity": 0.01
}
```

---

## `POST /robot/calibrate/move-z/stop`

Stoppe le déplacement Z en cours.

**Corps :** aucun

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
