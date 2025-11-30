import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import axios from 'axios'
import HistoryPage from '../pages/HistoryPage'

// Mock axios
vi.mock('axios')

const mockConversations = [
  {
    id: 1,
    filename: 'test-conversation-1.wav',
    status: 'processed',
    created_at: '2024-01-15T10:00:00Z',
    segments: [{ id: 1 }, { id: 2 }]
  },
  {
    id: 2,
    filename: 'test-conversation-2.wav',
    status: 'processing',
    created_at: '2024-01-16T12:00:00Z',
    segments: []
  },
  {
    id: 3,
    filename: 'test-conversation-3.wav',
    status: 'error',
    created_at: '2024-01-17T14:00:00Z',
    segments: []
  }
]

const renderHistoryPage = () => {
  return render(
    <BrowserRouter>
      <HistoryPage />
    </BrowserRouter>
  )
}

describe('HistoryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    axios.get.mockResolvedValue({ data: { conversations: mockConversations } })
  })

  it('renders the page title', async () => {
    renderHistoryPage()
    await waitFor(() => {
      expect(screen.getByText('Conversation History')).toBeInTheDocument()
    })
  })

  it('renders the description', async () => {
    renderHistoryPage()
    await waitFor(() => {
      expect(screen.getByText(/View and manage all your recorded conversations/)).toBeInTheDocument()
    })
  })

  it('shows loading spinner initially', () => {
    axios.get.mockReturnValue(new Promise(() => {})) // Never resolves
    renderHistoryPage()
    expect(document.querySelector('.loading-spinner')).toBeInTheDocument()
  })

  it('displays conversations after loading', async () => {
    renderHistoryPage()
    await waitFor(() => {
      expect(screen.getByText('test-conversation-1.wav')).toBeInTheDocument()
      expect(screen.getByText('test-conversation-2.wav')).toBeInTheDocument()
    })
  })

  it('displays statistics correctly', async () => {
    renderHistoryPage()
    await waitFor(() => {
      expect(screen.getByText('Total Conversations')).toBeInTheDocument()
      expect(screen.getByText('Processed')).toBeInTheDocument()
      expect(screen.getByText('Processing')).toBeInTheDocument()
      expect(screen.getByText('Errors')).toBeInTheDocument()
    })
  })

  it('renders search input', async () => {
    renderHistoryPage()
    await waitFor(() => {
      expect(screen.getByPlaceholderText('Search conversations...')).toBeInTheDocument()
    })
  })

  it('renders refresh button', async () => {
    renderHistoryPage()
    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument()
    })
  })

  it('renders Record New button', async () => {
    renderHistoryPage()
    await waitFor(() => {
      expect(screen.getByText('Record New')).toBeInTheDocument()
    })
  })

  it('displays empty state when no conversations', async () => {
    axios.get.mockResolvedValue({ data: { conversations: [] } })
    renderHistoryPage()
    await waitFor(() => {
      expect(screen.getByText('No conversations yet')).toBeInTheDocument()
    })
  })
})
