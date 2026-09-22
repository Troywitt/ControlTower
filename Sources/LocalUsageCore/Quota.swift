import Foundation

public enum Provider: String, CaseIterable, Codable, Sendable, Identifiable {
    case claude, codex, gemini, cursor, copilot, antigravity
    public var id: String { rawValue }
    public var title: String {
        switch self { case .claude: "Claude"; case .codex: "Codex"; case .gemini: "Gemini"; case .cursor: "Cursor"; case .copilot: "Copilot"; case .antigravity: "Antigravity" }
    }
    public var limitation: String {
        switch self {
        case .cursor: "Live access unavailable: upstream requires browser session cookies. Cookie harvesting is excluded."
        case .copilot: "Live access unavailable: upstream inferred unlimited Copilot usage from GitHub login. That does not establish a Copilot allowance."
        case .antigravity: "Live access unavailable: upstream probes local processes and extracts service credentials. Those probes are excluded."
        default: "Provider setup required."
        }
    }
}

public enum SafeError: Error, LocalizedError, Equatable, Sendable {
    case disabled, file, format, tooLarge
    public var errorDescription: String? {
        switch self {
        case .disabled: "Disconnected. No local data was read."
        case .file: "Cannot read the selected regular file. No alternate files were opened."
        case .format: "Unsupported local data. Use the documented quota feed or aggregate schema."
        case .tooLarge: "Selected data exceeds the size limit."
        }
    }
}

public struct QuotaWindow: Sendable, Identifiable, Equatable {
    public let id: String
    public let usedPercent: Double
    public let resetsAt: Date?
}
public struct QuotaSnapshot: Sendable, Equatable {
    public let provider: Provider
    public let windows: [QuotaWindow]
    public let fetchedAt: Date
}
