# RAGPilot Admin Dashboard

A Next.js admin dashboard for the RAGPilot intelligent document QA platform, built on the TailAdmin template.

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ 
- RAGPilot FastAPI backend running on `http://localhost:8080`

### Installation
```bash
cd src/frontend
npm install
npm run dev
```

The dashboard will be available at `http://localhost:3000` (or the next available port).

## 📁 Project Structure

```
src/frontend/
├── src/
│   ├── app/(admin)/          # Admin dashboard pages
│   ├── components/ragpilot/  # RAGPilot-specific components
│   ├── lib/                  # API client configuration
│   ├── services/             # API service layer
│   ├── types/                # TypeScript type definitions
│   └── providers/            # React Query provider
├── package.json
└── README_RAGPILOT.md
```

## 🎯 Current Features (MVP)

### Dashboard Overview
- **System Statistics**: Real-time stats for documents, chunks, queries, and users
- **Recent Documents**: List of recently uploaded documents with status
- **Quick Actions**: Navigation shortcuts to key features

### API Integration
- **Document Service**: Upload, list, delete, and manage documents
- **Admin Service**: System stats and configuration management
- **React Query**: Efficient data fetching with caching and background updates

### Components
- **SystemStatsCard**: Displays key system metrics
- **RecentDocuments**: Shows latest document uploads
- **DocumentStatusChart**: Placeholder for processing status visualization
- **QuickActions**: Quick navigation to common tasks

## 🔧 Configuration

### Environment Variables
Create a `.env.local` file in the frontend directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8080/api
NEXT_PUBLIC_APP_NAME=RAGPilot
NEXT_PUBLIC_APP_VERSION=1.0.0
```

### API Endpoints
The frontend connects to these FastAPI endpoints:
- `/api/admin/stats` - System statistics
- `/api/documents` - Document management
- `/api/admin/config/*` - Configuration management

## 📈 Next Steps

### Immediate Priorities
1. **Documents Page**: Full document management interface
2. **Upload Flow**: Drag-and-drop document upload
3. **Configuration Pages**: Admin settings for chunking, embeddings, etc.
4. **Authentication**: User login and permissions

### Future Enhancements
1. **Real-time Updates**: WebSocket integration for live status
2. **Analytics Dashboard**: Query analytics and usage metrics
3. **User Management**: Admin interface for user permissions
4. **Pipeline Monitoring**: Processing status and error tracking

## 🛠 Development

### Key Technologies
- **Next.js 15**: React framework with App Router
- **Tailwind CSS V4**: Utility-first styling
- **React Query**: Server state management
- **Axios**: HTTP client
- **TypeScript**: Type safety

### Code Organization
- **Services**: API calls abstracted into service layers
- **Types**: Shared TypeScript interfaces matching backend models
- **Components**: Reusable UI components following TailAdmin patterns
- **Providers**: React Query setup for data fetching

### Styling
Uses TailAdmin's design system with custom RAGPilot branding:
- Consistent color scheme and typography
- Dark/light mode support
- Responsive design patterns
- Accessible UI components

## 🔍 Troubleshooting

### Common Issues
1. **Module not found errors**: Ensure all RAGPilot components are created
2. **API connection failures**: Check backend is running on port 8080
3. **Build errors**: Verify all imports and TypeScript types

### Development Server
```bash
npm run dev     # Start development server
npm run build   # Build for production
npm run lint    # Run ESLint
```

## 📝 Contributing

When adding new features:
1. Follow existing patterns in `services/` and `components/ragpilot/`
2. Add TypeScript types to `types/ragpilot.ts`
3. Use React Query for data fetching
4. Follow TailAdmin's styling conventions 