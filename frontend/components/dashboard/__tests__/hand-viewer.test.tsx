import { render, screen, waitFor } from "@testing-library/react"
import { HandViewer } from "../hand-viewer"
import { fetchHandDetails, getHandNote } from "@/lib/api"
import { currency } from "@/lib/poker-data"

// Mock the API calls
jest.mock("@/lib/api", () => ({
  fetchHandDetails: jest.fn(),
  getHandNote: jest.fn(),
  saveHandNote: jest.fn(),
}))

describe("HandViewer", () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it("renders Date, Game Type, Final Pot, and Hero Result KPIs correctly when hand loads", async () => {
    // Arrange: mock the backend hand details
    const mockHandData = {
      hand_id: "HD-9999",
      date: "2023-10-15T20:00:00Z",
      data_limpa: "Oct 15, 2023 20:00",
      game_type: "Rush & Cash",
      stake_level: 0.1,
      platform: "GG Poker",
      player_nickname: "HeroName",
      hero_net_profit_usd: 25.5,
      hero_net_chips: 0,
      total_pot_final: 50.0,
      board_cards: ["Ah", "Kd", "Qs", "Jc", "10h"],
      player_cards: [{ player: "HeroName", cards: "Ac As" }],
      actions: []
    }

    const mockFetch = fetchHandDetails as jest.Mock
    mockFetch.mockResolvedValue(mockHandData)

    const mockGetNote = getHandNote as jest.Mock
    mockGetNote.mockResolvedValue({ note: "" })

    // Act: render component
    render(<HandViewer handId="HD-9999" onClose={jest.fn()} />)

    // Wait for the loading state to disappear
    await waitFor(() => {
      expect(screen.queryByText(/Loading hand data/i)).not.toBeInTheDocument()
    })

    // Assert: Check if KPI Labels exist
    expect(screen.getByText("Date")).toBeInTheDocument()
    expect(screen.getByText("Game Type")).toBeInTheDocument()
    expect(screen.getByText("Final Pot")).toBeInTheDocument()
    expect(screen.getByText("Hero Result")).toBeInTheDocument()

    // Assert: Check if the corresponding mocked values are rendered correctly
    // 1. Date
    expect(screen.getByText("Oct 15, 2023 20:00")).toBeInTheDocument()
    
    // 2. Game Type
    expect(screen.getByText("Rush & Cash")).toBeInTheDocument()
    
    // 3. Final Pot (Formatted as currency because game_type is Cash)
    expect(screen.getAllByText(currency(50.0))[0]).toBeInTheDocument()
    
    // 4. Hero Result (Formatted as positive currency since hero_net_profit > 0)
    expect(screen.getByText(`+${currency(25.5)}`)).toBeInTheDocument()
  })
})
