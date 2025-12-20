# Lumyn Playground

Interactive playground to try Lumyn Decision Records in your browser.

## Features

- **No Installation Required**: Runs in your browser
- **Interactive Examples**: Pre-built decision scenarios (refunds, risk blocks, memory similarity)
- **Monaco Editor**: VS Code-like editing experience
- **No User Data Required**: Everything starts with prepopulated sample inputs
- **No Network Calls**: Inputs are evaluated client-side and never sent anywhere

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

## Deployment

This playground is designed for deployment on Vercel (set the Vercel root directory to `playground/`).

It does not require any secrets.

## What it is (and isn't)

- The playground generates a **Decision Record-shaped** JSON result from your inputs to teach the contract.
- It uses a **minimal demo evaluator** (TypeScript) and does not run the full Lumyn engine in the browser.
