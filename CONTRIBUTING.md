# Contributing to Parallel Mind

Thank you for your interest in contributing to Parallel Mind! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/paraller_mind.git
   cd paraller_mind
   ```
3. **Add the upstream remote**:
   ```bash
   git remote add upstream https://github.com/talha307841/paraller_mind.git
   ```

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+
- At least 8GB RAM

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### Frontend Setup

```bash
cd frontend
npm install
```

### Running Locally

```bash
# Start all services with Docker
docker-compose up -d

# Or run individually:
# Backend
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm run dev
```

## Making Changes

1. **Create a branch** for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

2. **Make your changes** following our style guidelines

3. **Write or update tests** for your changes

4. **Run tests** to ensure everything passes:
   ```bash
   # Backend tests
   cd backend && pytest tests/ -v

   # Frontend tests
   cd frontend && npm test
   ```

5. **Commit your changes** with a clear message:
   ```bash
   git commit -m "feat: add new feature description"
   # or
   git commit -m "fix: resolve issue description"
   ```

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_api.py -v
```

### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:ui
```

## Pull Request Process

1. **Update documentation** if needed
2. **Ensure all tests pass**
3. **Update the README.md** if you're adding features
4. **Submit your pull request** with a clear description:
   - What changes were made
   - Why the changes were necessary
   - Any breaking changes
   - Screenshots (if UI changes)

5. **Address review feedback** promptly

## Style Guidelines

### Python (Backend)

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints where appropriate
- Document functions with docstrings
- Keep functions focused and small
- Use meaningful variable names

### JavaScript/React (Frontend)

- Follow ESLint configuration
- Use functional components with hooks
- Keep components small and focused
- Use meaningful prop names
- Add PropTypes or TypeScript types

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `style:` for formatting changes
- `refactor:` for code refactoring
- `test:` for adding tests
- `chore:` for maintenance tasks

### Documentation

- Update README.md for new features
- Add inline comments for complex logic
- Keep API documentation up-to-date
- Include examples where helpful

## Questions?

If you have questions, please:
1. Check existing issues
2. Open a new issue with your question
3. Tag it appropriately

Thank you for contributing to Parallel Mind! 🧠
