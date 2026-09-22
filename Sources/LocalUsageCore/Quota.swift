import Foundation

public enum Provider: String, CaseIterable, Codable, Sendable, Identifiable {
    case claude, codex, gemini, cursor, copilot, antigravity
    public var id: String { rawValue }
    public var title: String {
        switch self { case .claude: "Claude"; case .codex: "Codex"; case .gemini: "Gemini"; case .cursor: "Cursor"; case .copilot: "Copilot"; case .antigravity: "Antigravity" }
    }
    public var supportsLive: Bool { [.claude, .codex, .gemini].contains(self) }
    public var limitation: String {
        switch self {
        case .cursor: "Live access unavailable: upstream requires browser session cookies. Cookie harvesting is excluded."
        case .copilot: "Live access unavailable: upstream inferred unlimited Copilot usage from GitHub login. That does not establish a Copilot allowance."
        case .antigravity: "Live access unavailable: upstream probes local processes and extracts service credentials. Those probes are excluded."
        default: ""
        }
    }
    public var endpoint: URL? {
        switch self {
        case .claude: URL(string: "https://api.anthropic.com/api/oauth/usage")
        case .codex: URL(string: "https://chatgpt.com/backend-api/wham/usage")
        case .gemini: URL(string: "https://cloudcode-pa.googleapis.com/v1internal:retrieveUserQuota")
        default: nil
        }
    }
}

public enum SafeError: Error, LocalizedError, Equatable, Sendable {
    case unsupported, project, disabled, credentials, invalidToken, network, unauthorized, rateLimited, response, tooLarge, file, format
    public var errorDescription: String? {
        switch self {
        case .unsupported: "Live access is unavailable for this provider; no credentials were accessed."
        case .project: "Gemini requires an explicit Code Assist project ID; no discovery or provisioning is performed."
        case .disabled: "Disconnected. No credential or usage requests are made."
        case .credentials: "Saved access token unavailable. Reconnect explicitly; no other credential source was checked."
        case .invalidToken: "Enter a session access token without spaces or line breaks, not a password, API key or JSON document."
        case .network: "Usage request failed. No response body or credential details are shown."
        case .unauthorized: "Provider rejected this access token. Polling stopped. Reconnect explicitly."
        case .rateLimited: "Provider rate-limited this request. Polling stopped; retry manually later."
        case .response: "Provider returned unsupported or unavailable quota data."
        case .tooLarge: "Selected data exceeds the import or response size limit."
        case .file: "Cannot read the selected regular file. No alternate files were opened."
        case .format: "Unsupported usage data. Import a documented aggregate JSON file."
        }
    }
}

// No Codable conformance: never accidentally persist or log the whole credential.
public struct AccessCredential: Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    let token: String
    let accountID: String?
    public var description: String { "<redacted credential>" }
    public var debugDescription: String { description }
    public init(token: String, accountID: String? = nil) throws {
        let allowed = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~+/=")
        guard (20...16384).contains(token.utf8.count), token.unicodeScalars.allSatisfy(allowed.contains),
              !token.hasPrefix("sk-ant-api"), !token.hasPrefix("sk-proj-"), !token.hasPrefix("sk-svcacct-") else {
            throw SafeError.invalidToken
        }
        if let accountID, !accountID.isEmpty {
            let accountChars = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
            guard accountID.utf8.count <= 128, accountID.unicodeScalars.allSatisfy(accountChars.contains) else { throw SafeError.invalidToken }
        }
        self.token = token
        self.accountID = accountID.flatMap { $0.isEmpty ? nil : $0 }
    }
    public func validate(for provider: Provider) throws {
        guard provider.supportsLive else { throw SafeError.unsupported }
        // Shape checks reject common accidental passwords/API keys; they do NOT
        // prove authenticity, scope or that an opaque value is semantically an access token.
        switch provider {
        case .claude:
            guard token.hasPrefix("sk-ant-oat01-") else { throw SafeError.invalidToken }
        case .gemini:
            guard token.hasPrefix("ya29."), accountID != nil else {
                throw accountID == nil ? SafeError.project : SafeError.invalidToken
            }
        case .codex:
            let parts = token.split(separator: ".", omittingEmptySubsequences: false)
            guard parts.count == 3, parts.allSatisfy({ !$0.isEmpty }) else { throw SafeError.invalidToken }
            let raw = String(parts[0]).replacingOccurrences(of: "-", with: "+").replacingOccurrences(of: "_", with: "/")
            let padded = raw + String(repeating: "=", count: (4 - raw.count % 4) % 4)
            guard let data = Data(base64Encoded: padded),
                  let header = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let alg = header["alg"] as? String, ["RS256", "ES256", "EdDSA"].contains(alg) else { throw SafeError.invalidToken }
        default: throw SafeError.unsupported
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

public enum QuotaDecoder {
    public static let maxBytes = 128 * 1024
    public static func decode(_ data: Data, provider: Provider, now: Date = Date()) throws -> QuotaSnapshot {
        guard data.count <= maxBytes else { throw SafeError.tooLarge }
        guard let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw SafeError.response }
        var windows: [QuotaWindow] = []
        func number(_ value: Any?) -> Double? {
            guard let value = value as? NSNumber, CFGetTypeID(value) != CFBooleanGetTypeID() else { return nil }
            return value.doubleValue.isFinite ? value.doubleValue : nil
        }
        func append(_ value: Any?, label: String, percentKey: String, claude: Bool) throws {
            guard let obj = value as? [String: Any], let pct = number(obj[percentKey]) else { return }
            guard pct >= 0, pct <= 100 else { throw SafeError.response }
            let reset: Date?
            if claude, let text = obj["resets_at"] as? String {
                let format = ISO8601DateFormatter()
                format.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
                reset = format.date(from: text) ?? ISO8601DateFormatter().date(from: text)
            } else if let seconds = number(obj["reset_at"]), seconds >= 0, seconds < 32_503_680_000 {
                reset = Date(timeIntervalSince1970: seconds)
            } else if let seconds = number(obj["reset_after_seconds"]), seconds >= 0, seconds < 366 * 86400 {
                reset = now.addingTimeInterval(seconds)
            } else { reset = nil }
            windows.append(QuotaWindow(id: label, usedPercent: pct, resetsAt: reset))
        }
        if provider == .claude {
            for (key, label) in [("five_hour", "Session"), ("seven_day", "Weekly"), ("seven_day_sonnet", "Sonnet"), ("seven_day_opus", "Opus")] {
                try append(root[key], label: label, percentKey: "utilization", claude: true)
            }
        } else if provider == .gemini {
            guard let buckets = root["buckets"] as? [[String: Any]], buckets.count <= 100 else { throw SafeError.response }
            for bucket in buckets {
                guard let model = bucket["modelId"] as? String,
                      model.range(of: "^gemini-[a-zA-Z0-9._-]{1,70}$", options: .regularExpression) != nil,
                      let remaining = number(bucket["remainingFraction"]) else { continue }
                guard (0...1).contains(remaining) else { throw SafeError.response }
                // Keep each model's most constrained bucket; no invented plan/window length.
                if let old = windows.first(where: { $0.id == model }), old.usedPercent >= (1 - remaining) * 100 { continue }
                windows.removeAll { $0.id == model }
                try append(["utilization": (1 - remaining) * 100, "resets_at": bucket["resetTime"] ?? NSNull()], label: model, percentKey: "utilization", claude: true)
            }
        } else if provider == .codex, let rate = root["rate_limit"] as? [String: Any] {
            for (key, label) in [("primary_window", "Primary"), ("secondary_window", "Secondary")] {
                try append(rate[key], label: label, percentKey: "used_percent", claude: false)
            }
        }
        // Missing != zero. Never manufacture a full allowance.
        guard !windows.isEmpty else { throw SafeError.response }
        return QuotaSnapshot(provider: provider, windows: windows, fetchedAt: now)
    }
}

import CoreFoundation
