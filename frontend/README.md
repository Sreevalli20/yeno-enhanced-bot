# YeNo Research Console - Frontend

A professional React + TypeScript dashboard for the YeNo competition bot.

## Development

### Prerequisites
- Node.js 20+
- npm

### Setup
```bash
npm install
```

### Local Development
```bash
npm run dev
```

The app will be available at `http://localhost:5173`.

### Building for Production
```bash
npm run build
```

The production build will be in the `dist/` directory.

### Environment Variables

Create a `.env` file in the frontend directory:

```bash
# API Base URL for the backend
# Leave empty for same-origin deployment (frontend and backend on same server)
# Set to full URL for cross-origin deployment (e.g., https://your-backend.onrender.com)
VITE_API_BASE_URL=
```

See `.env.example` for the template.

## Deployment

The frontend should be deployed separately on Vercel.

### Vercel Deployment

1. Connect your GitHub repository to Vercel
2. Set the root directory to `frontend`
3. Configure build settings:
   - Framework Preset: Vite
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Install Command: `npm install`
4. Add environment variable:
   - `VITE_API_BASE_URL`: Set to `https://yeno-enhanced-bot.onrender.com`
5. Deploy

The backend (Python bot) is deployed separately on Render at https://yeno-enhanced-bot.onrender.com and serves the `/health` and `/decide` API endpoints.

## Tech Stack

- **React 19** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Lucide React** - Icon library

## Features

- Professional quantitative-research dashboard aesthetic
- Dark theme with navy/charcoal background
- Decision workspace with JSON input and validation
- Real-time backend health monitoring
- API documentation
- Responsive design for desktop, tablet, and mobile
- Accessible components with keyboard navigation
