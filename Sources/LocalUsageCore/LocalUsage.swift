import Foundation

/// Strict user-authored/exported aggregate schema. No transcript, auth JSON or folder scanner.
public struct LocalUsageRow: Codable, Identifiable, Sendable, Equatable {
    public let id: String
    public let provider: Provider
    public let date: String
    public let model: String
    public let inputTokens: Int
    public let cachedInputTokens: Int
    public let outputTokens: Int
    public var totalTokens: Int { inputTokens + cachedInputTokens + outputTokens }
    public func estimate(inputRate: Double, cachedRate: Double, outputRate: Double) -> Double {
        (Double(inputTokens) * inputRate + Double(cachedInputTokens) * cachedRate + Double(outputTokens) * outputRate) / 1_000_000
    }
}
public enum AggregateImporter {
    public static let maxBytes = 4 * 1024 * 1024
    /// Gate BEFORE invoking the supplied reader. Caller supplies only an explicitly selected file.
    public static func load(provider: Provider, enabled: Bool, read: () throws -> Data) throws -> [LocalUsageRow] {
        guard enabled else { throw SafeError.disabled }
        let data: Data
        do { data = try read() } catch let error as SafeError { throw error } catch { throw SafeError.file }
        guard data.count <= maxBytes else { throw SafeError.tooLarge }
        let fields: Set<String> = ["id", "provider", "date", "model", "inputTokens", "cachedInputTokens", "outputTokens"]
        guard let objects = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]], objects.count <= 10000,
              objects.allSatisfy({ Set($0.keys) == fields }),
              let rows = try? JSONDecoder().decode([LocalUsageRow].self, from: data) else { throw SafeError.format }
        var ids = Set<String>()
        let calendar = Calendar(identifier: .gregorian)
        for row in rows {
            let parts = row.date.split(separator: "-").compactMap { Int($0) }
            guard parts.count == 3, row.date.count == 10, (2000...2200).contains(parts[0]),
                  let date = calendar.date(from: DateComponents(year: parts[0], month: parts[1], day: parts[2])),
                  calendar.component(.year, from: date) == parts[0], calendar.component(.month, from: date) == parts[1],
                  calendar.component(.day, from: date) == parts[2],
                  row.provider == provider,
                  [row.inputTokens, row.cachedInputTokens, row.outputTokens].allSatisfy({ (0...1_000_000_000_000).contains($0) }),
                  row.model.range(of: "^[a-zA-Z0-9._-]{1,80}$", options: .regularExpression) != nil,
                  row.id.range(of: "^[a-zA-Z0-9._-]{1,80}$", options: .regularExpression) != nil,
                  ids.insert(row.id).inserted else { throw SafeError.format }
        }
        return rows.sorted { ($0.date, $0.id) < ($1.date, $1.id) }
    }
}
