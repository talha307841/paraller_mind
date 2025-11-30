import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { MemoryRouter } from 'react-router-dom'
import axios from 'axios'
import ConversationDetailPage from '../pages/ConversationDetailPage'

// Mock axios
vi.mock('axios')

const mockConversation = {
  id: 1,
  filename: 'test-conversation.wav',
  status: 'processed',
  created_at: '2024-01-15T10:00:00Z',
  segments: [
    {
      id: 1,
      speaker_label: 'SPEAKER_00',
      text: 'Hello, how are you?',
      start_time: 0,
      end_time: 2.5,
      confidence: 0.95
    },
    {
      id: 2,
      speaker_label: 'SPEAKER_01',
      text: 'I am doing great, thank you!',
      start_time: 2.5,
      end_time: 5.0,
      confidence: 0.92
    }
  ]
}

const renderConversationDetailPage = (conversationId = '1') => {
  return render(
    <MemoryRouter initialEntries={[`/conversation/${conversationId}`]}>
      <Routes>
        <Route path="/conversation/:id" element={<ConversationDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ConversationDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    axios.get.mockResolvedValue({ data: mockConversation })
    axios.post.mockResolvedValue({ data: { summary: 'Test summary', key_points: [] } })
  })

  it('shows loading spinner initially', () => {
    axios.get.mockReturnValue(new Promise(() => {}))
    renderConversationDetailPage()
    expect(document.querySelector('.loading-spinner')).toBeInTheDocument()
  })

  it('displays conversation filename', async () => {
    renderConversationDetailPage()
    await waitFor(() => {
      expect(screen.getByText(/test-conversation.wav/)).toBeInTheDocument()
    })
  })

  it('displays Back to History link', async () => {
    renderConversationDetailPage()
    await waitFor(() => {
      expect(screen.getByText('Back to History')).toBeInTheDocument()
    })
  })

  it('displays search section', async () => {
    renderConversationDetailPage()
    await waitFor(() => {
      expect(screen.getByText('Search Conversation')).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/Search for specific topics/)).toBeInTheDocument()
    })
  })

  it('displays AI Summary section', async () => {
    renderConversationDetailPage()
    await waitFor(() => {
      expect(screen.getByText('AI Summary')).toBeInTheDocument()
    })
  })

  it('displays Suggested Replies section', async () => {
    renderConversationDetailPage()
    await waitFor(() => {
      expect(screen.getByText('Suggested Replies')).toBeInTheDocument()
    })
  })

  it('displays Conversation Transcript section', async () => {
    renderConversationDetailPage()
    await waitFor(() => {
      expect(screen.getByText('Conversation Transcript')).toBeInTheDocument()
    })
  })

  it('displays transcript segments', async () => {
    renderConversationDetailPage()
    await waitFor(() => {
      expect(screen.getByText('Hello, how are you?')).toBeInTheDocument()
      expect(screen.getByText('I am doing great, thank you!')).toBeInTheDocument()
    })
  })

  it('displays speaker labels', async () => {
    renderConversationDetailPage()
    await waitFor(() => {
      expect(screen.getByText('SPEAKER_00')).toBeInTheDocument()
      expect(screen.getByText('SPEAKER_01')).toBeInTheDocument()
    })
  })

  it('displays segment count', async () => {
    renderConversationDetailPage()
    await waitFor(() => {
      // Use getAllByText since segment count appears in multiple places
      const segmentElements = screen.getAllByText(/2.*segments/i)
      expect(segmentElements.length).toBeGreaterThan(0)
    })
  })

  it('displays not found message for invalid conversation', async () => {
    axios.get.mockResolvedValue({ data: null })
    renderConversationDetailPage('999')
    await waitFor(() => {
      expect(screen.getByText('Conversation Not Found')).toBeInTheDocument()
    })
  })
})
