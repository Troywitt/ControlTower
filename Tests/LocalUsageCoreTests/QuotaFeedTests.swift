import Foundation
import Testing
@testable import LocalUsageCore

@Suite struct QuotaFeedTests {
    func data(_ changes: [String: Any] = [:]) throws -> Data {
        var value: [String: Any] = ["version": 1, "provider": "claude", "observedAt": 1000,
                                   "windows": [["id": "Session", "usedPercent": 34, "resetsAt": 2000]]]
        value.merge(changes) { _, new in new }
        return try JSONSerialization.data(withJSONObject: value)
    }
    @Test func validAndStaleRemainDistinct() throws {
        let result = try QuotaFeed.decode(data(), provider: .claude, now: Date(timeIntervalSince1970: 1400))
        #expect(result.windows.first?.usedPercent == 34)
        #expect(Date(timeIntervalSince1970: 1400).timeIntervalSince(result.fetchedAt) > QuotaFeed.staleAfter)
    }
    @Test func missingIsNotZero() throws {
        let result = try QuotaFeed.decode(data(["windows": []]), provider: .claude, now: Date(timeIntervalSince1970: 1000))
        #expect(result.windows.isEmpty)
    }
    @Test func wrongProviderExtraFieldsFutureAndBooleansRejected() throws {
        for changes: [String: Any] in [["provider": "codex"], ["token": "synthetic-secret"], ["observedAt": 100000],
                                      ["observedAt": true], ["windows": [["id": "Session", "usedPercent": true]]],
                                      ["windows": [["id": "Session", "usedPercent": 101]]]] {
            #expect(throws: SafeError.self) { try QuotaFeed.decode(data(changes), provider: .claude, now: Date(timeIntervalSince1970: 1000)) }
        }
    }
    @Test func duplicateAndOversizeRejected() throws {
        #expect(throws: SafeError.self) { try QuotaFeed.decode(Data(repeating: 32, count: 8193), provider: .claude) }
        let row: [String: Any] = ["id": "Session", "usedPercent": 12]
        #expect(throws: SafeError.self) { try QuotaFeed.decode(data(["windows": [row, row]]), provider: .claude) }
    }
    @Test func activeAggregateImporterStillRequiresConsentAndRejectsCredentials() throws {
        #expect(throws: SafeError.self) {
            try AggregateImporter.load(provider: .claude, enabled: false) { Issue.record("Disabled reader invoked"); return Data() }
        }
        #expect(throws: SafeError.self) {
            try AggregateImporter.load(provider: .claude, enabled: true) { Data("[{\"token\":\"synthetic\"}]".utf8) }
        }
    }
}
