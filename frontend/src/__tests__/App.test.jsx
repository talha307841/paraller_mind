import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import App from '../App'

const renderApp = () => {
  return render(
    <BrowserRouter>
      <App />
    </BrowserRouter>
  )
}

describe('App', () => {
  it('renders the header with title', () => {
    render(<App />)
    expect(screen.getByText('🧠 Parallel Mind')).toBeInTheDocument()
  })

  it('renders the subtitle', () => {
    render(<App />)
    expect(screen.getByText('Advanced Conversational AI with Audio Intelligence')).toBeInTheDocument()
  })

  it('renders the footer', () => {
    render(<App />)
    expect(screen.getByText(/2024 Parallel Mind/)).toBeInTheDocument()
  })

  it('has proper header styling with gradient', () => {
    render(<App />)
    const header = document.querySelector('header')
    expect(header).toHaveClass('bg-gradient-to-r', 'from-blue-600', 'to-purple-600')
  })
})
