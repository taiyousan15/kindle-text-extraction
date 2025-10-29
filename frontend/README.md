# Kindle OCR Frontend

Modern React/Next.js frontend for the Kindle OCR & RAG System.

## Features

- **Modern UI**: Built with React 18, Next.js 14, and Tailwind CSS
- **Type-Safe**: Full TypeScript support
- **Real-time Updates**: React Query for efficient data fetching
- **Responsive Design**: Mobile-friendly interface
- **Dark Mode**: Theme switching support
- **Drag & Drop**: Easy file uploads with react-dropzone
- **Toast Notifications**: User-friendly feedback with Sonner

## Tech Stack

### Core
- **Next.js 14** - React framework with App Router
- **React 18** - UI library
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first CSS framework

### UI Components
- **Radix UI** - Accessible component primitives
- **Lucide React** - Beautiful icon library
- **Sonner** - Toast notifications
- **Recharts** - Data visualization

### State & Data
- **React Query** - Server state management
- **Zustand** - Client state management
- **Axios** - HTTP client

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn or pnpm
- FastAPI backend running on http://localhost:8000

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Copy environment variables
cp .env.local.example .env.local

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME="Kindle OCR"
NEXT_PUBLIC_APP_VERSION="2.0.0"
```

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── page.tsx           # Dashboard
│   │   ├── upload/            # OCR Upload page
│   │   ├── capture/           # Auto Capture page
│   │   ├── rag/               # RAG Search page
│   │   ├── jobs/              # Jobs Management page
│   │   ├── knowledge/         # Knowledge Base page
│   │   ├── layout.tsx         # Root layout
│   │   └── globals.css        # Global styles
│   ├── components/
│   │   ├── layout/            # Layout components
│   │   │   ├── sidebar.tsx
│   │   │   ├── header.tsx
│   │   │   └── main-layout.tsx
│   │   ├── dashboard/         # Dashboard components
│   │   ├── ui/                # Reusable UI components
│   │   └── providers.tsx      # App providers
│   ├── lib/
│   │   ├── api.ts             # API client & functions
│   │   └── utils.ts           # Utility functions
│   ├── hooks/                 # Custom React hooks
│   ├── store/                 # Zustand stores
│   └── types/                 # TypeScript types
├── public/                    # Static files
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.mjs
```

## Available Scripts

```bash
# Development
npm run dev          # Start dev server (http://localhost:3000)

# Production
npm run build        # Build for production
npm run start        # Start production server

# Code Quality
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript compiler
```

## Pages

### Dashboard (/)
- System overview and statistics
- Recent jobs display
- Quick action buttons
- Health status monitoring

### OCR Upload (/upload)
- Drag & drop file upload
- Image preview
- Real-time OCR processing
- Text extraction results
- Download extracted text

### Auto Capture (/capture)
- Amazon authentication
- Kindle Cloud Reader integration
- Progress tracking
- Batch OCR processing

### RAG Search (/rag)
- Natural language questions
- AI-powered answers
- Source citations
- Book-specific filtering

### Jobs Management (/jobs)
- All jobs listing
- Status filtering
- Job details
- Progress tracking

### Knowledge Base (/knowledge)
- Extracted insights
- Key concepts
- Searchable knowledge

## API Integration

The frontend communicates with the FastAPI backend through `src/lib/api.ts`.

### Key API Functions

```typescript
// Health check
api.health()

// OCR
api.uploadImage(file, bookTitle, pageNum)

// Capture
api.startCapture(captureRequest)
api.getJob(jobId)
api.listJobs(limit)

// RAG
api.askQuestion(ragRequest)

// Knowledge
api.extractKnowledge(bookTitle)
api.listKnowledge()
```

## Styling

### Tailwind CSS

Utility-first CSS framework for rapid UI development.

```tsx
<div className="flex items-center space-x-4 rounded-lg border p-4">
  <h2 className="text-2xl font-bold">Title</h2>
</div>
```

### Dark Mode

Theme switching with next-themes:

```tsx
import { useTheme } from "next-themes";

const { theme, setTheme } = useTheme();
setTheme("dark"); // or "light"
```

### Custom Colors

Defined in `tailwind.config.ts` and `globals.css`:

```css
--primary: 221.2 83.2% 53.3%;
--secondary: 210 40% 96.1%;
--destructive: 0 84.2% 60.2%;
```

## Data Fetching

### React Query

Efficient server state management:

```tsx
const { data, isLoading, error } = useQuery(
  "jobs",
  () => api.listJobs(10),
  {
    refetchInterval: 5000, // Auto-refresh every 5s
  }
);
```

### Mutations

Handle data updates:

```tsx
const mutation = useMutation(
  (data) => api.uploadImage(data),
  {
    onSuccess: () => toast.success("Success!"),
    onError: (error) => toast.error(error.message),
  }
);
```

## Deployment

### Production Build

```bash
npm run build
npm run start
```

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

### Environment Variables (Production)

```env
NEXT_PUBLIC_API_BASE_URL=https://api.your-domain.com
NODE_ENV=production
```

## Performance

- **Code Splitting**: Automatic route-based splitting
- **Image Optimization**: Next.js Image component
- **Lazy Loading**: Components loaded on demand
- **Caching**: React Query cache management

## Troubleshooting

### API Connection Error

**Problem**: Cannot connect to FastAPI backend

**Solution**:
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check `NEXT_PUBLIC_API_BASE_URL` in `.env.local`
3. Ensure CORS is configured in FastAPI

### Build Errors

**Problem**: TypeScript errors during build

**Solution**:
```bash
npm run type-check  # Check for type errors
npm run lint        # Check for linting errors
```

### Styling Not Applied

**Problem**: Tailwind styles not working

**Solution**:
1. Verify `tailwind.config.ts` paths
2. Check `globals.css` imports `@tailwind` directives
3. Restart dev server

## Contributing

1. Create feature branch
2. Make changes
3. Run type-check and lint
4. Submit pull request

## License

MIT License - see LICENSE file

## Support

- **Documentation**: See [main README](../README.md)
- **Issues**: [GitHub Issues](https://github.com/taiyousan15/kindle-text-extraction/issues)
- **Backend API**: http://localhost:8000/docs

---

**Built with Next.js 14 & React 18** | **Kindle OCR Frontend v2.0.0**
