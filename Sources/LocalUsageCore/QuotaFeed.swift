import Foundation

/// Strict quota-only boundary shared by the provider-owned local adapters.
public enum QuotaFeed {
    public static let maxBytes = 8192
    public static let staleAfter: TimeInterval = 300
    public static func decode(_ data: Data, provider: Provider, now: Date = Date()) throws -> QuotaSnapshot {
        guard data.count <= maxBytes, [.claude, .codex, .gemini].contains(provider),
              let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              Set(root.keys) == ["version", "provider", "observedAt", "windows"],
              let version = root["version"] as? NSNumber, CFGetTypeID(version) != CFBooleanGetTypeID(), version == 1,
              root["provider"] as? String == provider.rawValue,
              let stamp = root["observedAt"] as? NSNumber, CFGetTypeID(stamp) != CFBooleanGetTypeID(),
              stamp.doubleValue.isFinite, stamp.doubleValue > 0, stamp.doubleValue <= now.timeIntervalSince1970 + 30,
              let rows = root["windows"] as? [[String: Any]], rows.count <= 8 else { throw SafeError.format }
        var seen: Set<String> = []
        let allowedIDs = provider == .claude ? ["Session", "Weekly"] : provider == .codex ? ["Primary", "Secondary"] : ["Pro", "Flash", "Flash Lite"]
        let windows = try rows.map { row -> QuotaWindow in
            guard Set(row.keys).isSubset(of: ["id", "usedPercent", "resetsAt"]),
                  let id = row["id"] as? String, allowedIDs.contains(id),
                  seen.insert(id).inserted,
                  let pct = row["usedPercent"] as? NSNumber, CFGetTypeID(pct) != CFBooleanGetTypeID(),
                  pct.doubleValue.isFinite, (0...100).contains(pct.doubleValue) else { throw SafeError.format }
            var reset: Date?
            if let value = row["resetsAt"] {
                guard let seconds = value as? NSNumber, CFGetTypeID(seconds) != CFBooleanGetTypeID(),
                      seconds.doubleValue.isFinite, (0...32_503_680_000).contains(seconds.doubleValue) else { throw SafeError.format }
                reset = Date(timeIntervalSince1970: seconds.doubleValue)
            }
            return QuotaWindow(id: id, usedPercent: pct.doubleValue, resetsAt: reset)
        }
        return QuotaSnapshot(provider: provider, windows: windows, fetchedAt: Date(timeIntervalSince1970: stamp.doubleValue))
    }
}

import CoreFoundation
