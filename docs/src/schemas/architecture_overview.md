---
config:
  layout: elk
---
flowchart TB
    subgraph FRONTEND["Frontend  (React / Vite)"]
        UI["Interface utilisateur\n(plateau, leaderboard, calibration)"]
    end

    subgraph API["manipulation_robot / api.py  (FastAPI)"]
        direction TB
        APIGW["api.py\n(REST + WebSocket)"]
        CM["chess_manager.py\n(logique du jeu)"]
        RC["robot_controller.py\n(commandes RTDE)"]
        CAL["calibration.py\n(procédure de calibration)"]
        BRM["board_reset_manager.py\n(remise en position)"]
        HBM["hybrid_board_manager.py\n(état hybride caméra + logique)"]
        LB["leaderboard_manager.py"]

        APIGW --> CM
        APIGW --> CAL
        APIGW --> BRM
        APIGW --> LB
        CM --> RC
        CM --> HBM
        BRM --> HBM
    end

    subgraph VISION["chess_vision  (pipeline vision)"]
        direction TB
        INF["infinite_chess_vision.py\n(boucle continue ~2s)"]
        PIPE["ChessVisionPipeline\n(caméra → ArUco → cases → JSON)"]
        INF --> PIPE
    end

    subgraph STOCKFISH["Moteur IA"]
        SF["Stockfish\n(protocole UCI)"]
    end

    subgraph ROBOT_HW["Matériel"]
        UR["Robot UR\n(192.168.0.11 — RTDE)"]
        CAM["Caméra USB"]
    end

    subgraph CONFIG_JSON["JSON de configuration  (écrits à la calibration, lus au démarrage)"]
        BC["board_calibration.json\n(coins plateau en pixels)"]
        RBC["robot_calibration.json\n(points A1 & H8 en XYZ)"]
        PDR["position_depart_robot.json\n(pose initiale du bras)"]
    end

    subgraph DATA_JSON["Données vivantes  (mis à jour en continu)"]
        direction TB
        DN["output/data_N/\n├─ game_state.json\n├─ board_state.json\n├─ coordinates.json\n└─ 1_original.jpg … 6_aruco.jpg"]
        SYM["output/latest/\n(symlink → data_N le plus récent)"]
        LBD["leaderboard_data.json"]
        DN --> SYM
    end
    UI <-->|"REST / WebSocket"| APIGW
    RC <-->|"RTDE (TCP)"| UR
    RC -->|"lit"| RBC
    RC -->|"lit"| PDR
    CAL -->|"écrit"| RBC
    CAL -.->|"déclenche calibrate_board.py"| BC
    CAM -->|"frames"| PIPE
    PIPE -->|"lit"| BC
    PIPE -->|"écrit"| DN
    SYM -->|"lit game_state.json"| BRM
    SYM -->|"lit game_state.json"| HBM
    CM <-->|"UCI"| SF
    LB -->|"lit / écrit"| LBD
    style FRONTEND fill:#e2d9f3,stroke:#6f42c1,color:#000
    style API fill:#f8d7da,stroke:#721c24,color:#000
    style VISION fill:#cce5ff,stroke:#004085,color:#000
    style STOCKFISH fill:#ffeeba,stroke:#856404,color:#000
    style ROBOT_HW fill:#d6d8d9,stroke:#495057,color:#000
    style CONFIG_JSON fill:#fff3cd,stroke:#e6a817,color:#000
    style DATA_JSON fill:#d4edda,stroke:#28a745,color:#000