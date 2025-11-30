import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import HomePage from '../pages/HomePage'

// Mock the AudioRecorder component
vi.mock('../components/AudioRecorder', () => ({
  default: ({ onUploadComplete }) => (
    <div data-testid="mock-audio-recorder">Mock Audio Recorder</div>
  )
}))

const renderHomePage = () => {
  return render(
    <BrowserRouter>
      <HomePage />
    </BrowserRouter>
  )
}

describe('HomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the welcome title', () => {
    renderHomePage()
    expect(screen.getByText(/Welcome to/)).toBeInTheDocument()
    expect(screen.getByText('Parallel Mind')).toBeInTheDocument()
  })

  it('renders the description', () => {
    renderHomePage()
    expect(screen.getByText(/Advanced AI-powered conversation analysis/)).toBeInTheDocument()
  })

  it('renders the feature cards', () => {
    renderHomePage()
    expect(screen.getByText('Smart Recording')).toBeInTheDocument()
    expect(screen.getByText('AI Analysis')).toBeInTheDocument()
    expect(screen.getByText('Semantic Search')).toBeInTheDocument()
  })

  it('renders the AudioRecorder component', () => {
    renderHomePage()
    expect(screen.getByTestId('mock-audio-recorder')).toBeInTheDocument()
  })

  it('renders the How It Works section', () => {
    renderHomePage()
    expect(screen.getByText('How It Works')).toBeInTheDocument()
    expect(screen.getByText('Record')).toBeInTheDocument()
    expect(screen.getByText('Process')).toBeInTheDocument()
    expect(screen.getByText('Analyze')).toBeInTheDocument()
    expect(screen.getByText('Insights')).toBeInTheDocument()
  })

  it('renders the quick action links', () => {
    renderHomePage()
    expect(screen.getByText('Conversation History')).toBeInTheDocument()
    expect(screen.getByText('AI Insights')).toBeInTheDocument()
  })

  it('contains link to history page', () => {
    renderHomePage()
    const historyLink = screen.getByRole('link', { name: /Conversation History/i })
    expect(historyLink).toHaveAttribute('href', '/history')
  })
})
