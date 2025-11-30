import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import AudioRecorder from '../components/AudioRecorder'

// Mock MediaRecorder
class MockMediaRecorder {
  constructor(stream) {
    this.stream = stream
    this.ondataavailable = null
    this.onstop = null
    this.state = 'inactive'
  }

  start() {
    this.state = 'recording'
  }

  stop() {
    this.state = 'inactive'
    if (this.onstop) {
      this.onstop()
    }
  }
}

global.MediaRecorder = MockMediaRecorder

describe('AudioRecorder', () => {
  const mockOnUploadComplete = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the recording section', () => {
    render(<AudioRecorder onUploadComplete={mockOnUploadComplete} />)
    expect(screen.getByText('Record Your Conversation')).toBeInTheDocument()
  })

  it('renders the instructions', () => {
    render(<AudioRecorder onUploadComplete={mockOnUploadComplete} />)
    expect(screen.getByText(/Ensure good audio quality/)).toBeInTheDocument()
    expect(screen.getByText(/Speak clearly/)).toBeInTheDocument()
    expect(screen.getByText(/Processing may take/)).toBeInTheDocument()
  })

  it('shows start recording button initially', () => {
    render(<AudioRecorder onUploadComplete={mockOnUploadComplete} />)
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
  })

  it('displays click to start message', () => {
    render(<AudioRecorder onUploadComplete={mockOnUploadComplete} />)
    expect(screen.getByText('Click the microphone to start recording')).toBeInTheDocument()
  })
})
