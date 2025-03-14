# CLAUDE.md - ProtonDemand Development Guide

## Build Commands
- `npm run dev` - Start development server
- `npm run build` - Build production version
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## Code Style Guidelines
- Use TypeScript with strict mode enabled
- Import ordering: React first, then external libs, then internal modules
- Use absolute imports with @ alias (e.g., `@/components/ui/button`)
- Component naming: PascalCase for components, camelCase for functions/hooks
- Interface naming: PascalCase with 'I' prefix optional (e.g., `ButtonProps`)
- Use functional components with React.forwardRef when needed
- Leverage TypeScript interfaces for all props and API responses
- Error handling: Use try/catch blocks with specific error types and messages
- UI components: Use shadcn/ui patterns with Tailwind for styling
- State management: Prefer React hooks (useState, useContext) for component state

## API Error Handling
Follow the pattern of returning NextResponse.json with appropriate status codes and error messages:
```typescript
return NextResponse.json({ 
  success: false, 
  error: 'Error message'
}, { status: 400 });
```