# Sentinel Frontend

This is a minimal Vite + React frontend for the Sentinel project. It includes:
- Chat page: send prompts as `User_A` or `User_Attacker` (attacker has a spam button).
- Admin dashboard: polls the gateway every 3s and shows Users, Query Log, and Threat Log.

Quick start
1. From repo root copy the main `.env` values into a frontend `.env` (or create a project .env):

   VITE_REACT_APP_API_URL=http://localhost:3001/api/v1

2. Install and run:

   cd frontend
   npm install
   npm run dev

Notes
- The frontend expects the Gateway API (gateway-node) to be running and reachable at `VITE_REACT_APP_API_URL`.
- The project root `.env` contains service URLs and ports; you can reuse `REACT_APP_API_URL` or set `VITE_REACT_APP_API_URL` for the frontend.
