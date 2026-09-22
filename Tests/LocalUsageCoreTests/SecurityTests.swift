import Foundation
import Testing
@testable import LocalUsageCore

private let syntheticToken = "synthetic-ONLY-test-access-token-1234567890"
private func token(_ provider: Provider) -> String {
    switch provider {
    case .claude: "sk-ant-oat01-" + syntheticToken
    case .gemini: "ya29." + syntheticToken
    default: "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJTWU5USEVUSUMifQ.fake-signature-ONLY"
    }
}
private final class VaultSpy: CredentialVault, @unchecked Sendable {
    private let lock = NSLock()
    private var values: [Provider: AccessCredential] = [:]
    private var counts = [0, 0, 0]
    var calls: [Int] { lock.withLock { counts } }
    func save(_ credential: AccessCredential, for provider: Provider) throws { lock.withLock { counts[0] += 1; values[provider] = credential } }
    func load(for provider: Provider) throws -> AccessCredential {
        try lock.withLock { counts[1] += 1; guard let value = values[provider] else { throw SafeError.credentials }; return value }
    }
    func remove(for provider: Provider) throws { lock.withLock { counts[2] += 1; values[provider] = nil } }
}
private actor TransportSpy: QuotaTransport {
    var calls = 0
    var fail: SafeError?
    init(fail: SafeError? = nil) { self.fail = fail }
    func fetch(provider: Provider, credential: AccessCredential) async throws -> QuotaSnapshot {
        calls += 1
        if let fail { throw fail }
        return QuotaSnapshot(provider: provider, windows: [QuotaWindow(id: "Test", usedPercent: 25, resetsAt: nil)], fetchedAt: .distantPast)
    }
}
private actor SuspendedTransport: QuotaTransport {
    private var waiter: CheckedContinuation<QuotaSnapshot, Never>?
    private var started: CheckedContinuation<Void, Never>?
    func fetch(provider: Provider, credential: AccessCredential) async throws -> QuotaSnapshot {
        await withCheckedContinuation { continuation in waiter = continuation; started?.resume(); started = nil }
    }
    func waitUntilStarted() async { if waiter != nil { return }; await withCheckedContinuation { started = $0 } }
    func finish(_ provider: Provider) { waiter?.resume(returning: QuotaSnapshot(provider: provider, windows: [], fetchedAt: .distantPast)); waiter = nil }
}

@MainActor
struct BrokerTests {
    @Test func testStartupAndDisabledMakeZeroCredentialOrNetworkCallsForEveryProvider() async throws {
        let vault = VaultSpy(); let transport = TransportSpy()
        let broker = CredentialBroker(vault: vault, transport: transport)
        for provider in Provider.allCases {
            do { _ = try await broker.fetch(provider); XCTFail("Must not fetch") } catch { }
            broker.disable(provider)
        }
        XCTAssertEqual(vault.calls, [0, 0, 0])
        let calls = await transport.calls; XCTAssertEqual(calls, 0)
    }
    @Test func testOptInIsPerProviderAndDisableStopsAllLaterIO() async throws {
        let vault = VaultSpy(); let transport = TransportSpy(); let broker = CredentialBroker(vault: vault, transport: transport)
        try broker.connect(.claude, credential: AccessCredential(token: token(.claude)))
        _ = try await broker.fetch(.claude)
        do { _ = try await broker.fetch(.codex); XCTFail() } catch { }
        broker.disable(.claude)
        for _ in 0..<3 { do { _ = try await broker.fetch(.claude); XCTFail() } catch { } }
        XCTAssertEqual(vault.calls, [1, 1, 0]); let calls = await transport.calls; XCTAssertEqual(calls, 1)
    }
    @Test func testGeminiRequiresExplicitProjectBeforeAnyKeychainIO() async throws {
        let vault = VaultSpy(); let transport = TransportSpy(); let broker = CredentialBroker(vault: vault, transport: transport)
        do { try broker.connect(.gemini, credential: AccessCredential(token: token(.gemini))); XCTFail() }
        catch { XCTAssertEqual(error as? SafeError, .project) }
        XCTAssertEqual(vault.calls, [0, 0, 0])
        try broker.connect(.gemini, credential: AccessCredential(token: token(.gemini), accountID: "test-project"))
        _ = try await broker.fetch(.gemini)
        XCTAssertEqual(vault.calls, [1, 1, 0])
    }
    @Test func testUnavailableProvidersNeverAccessVaultEvenOnExplicitConnect() async throws {
        let vault = VaultSpy(); let transport = TransportSpy(); let broker = CredentialBroker(vault: vault, transport: transport)
        for provider in Provider.allCases.filter({ !$0.supportsLive }) {
            do { try broker.connect(provider, credential: AccessCredential(token: syntheticToken)); XCTFail() } catch { }
            broker.enableSaved(provider)
            do { _ = try await broker.fetch(provider); XCTFail() } catch { }
            do { try broker.removeSaved(provider); XCTFail() } catch { }
        }
        XCTAssertEqual(vault.calls, [0, 0, 0]); let calls = await transport.calls; XCTAssertEqual(calls, 0)
    }
    @Test func testFailureStopsPollingWithoutFallbackOrRepeatedKeychainReads() async throws {
        for failure in [SafeError.unauthorized, .rateLimited, .network, .response] {
            let vault = VaultSpy(); let transport = TransportSpy(fail: failure); let broker = CredentialBroker(vault: vault, transport: transport)
            try broker.connect(.codex, credential: AccessCredential(token: token(.codex)))
            do { _ = try await broker.fetch(.codex); XCTFail() } catch { XCTAssertEqual(error as? SafeError, failure) }
            do { _ = try await broker.fetch(.codex); XCTFail() } catch { XCTAssertEqual(error as? SafeError, .disabled) }
            XCTAssertEqual(vault.calls, [1, 1, 0]); let calls = await transport.calls; XCTAssertEqual(calls, 1)
        }
    }
    @Test func testDisableRejectsLateResultEvenIfTransportIgnoresCancellation() async throws {
        let vault = VaultSpy(); let transport = SuspendedTransport(); let broker = CredentialBroker(vault: vault, transport: transport)
        try broker.connect(.claude, credential: AccessCredential(token: token(.claude)))
        let fetch = Task { try await broker.fetch(.claude) }
        await transport.waitUntilStarted()
        broker.disable(.claude)
        await transport.finish(.claude)
        do { _ = try await fetch.value; XCTFail("Late response must be discarded") } catch { XCTAssertEqual(error as? SafeError, .disabled) }
    }
    @Test func testQueuedFetchCancelledBeforeExecutionDoesNotReadCredential() async throws {
        let vault = VaultSpy(); let transport = TransportSpy()
        let broker = CredentialBroker(vault: vault, transport: transport)
        try broker.connect(.claude, credential: AccessCredential(token: token(.claude)))
        // Same MainActor as UI: revoke synchronously before queued refresh gets a turn.
        let queued = Task { try await broker.fetch(.claude) }
        broker.disable(.claude); queued.cancel()
        do { _ = try await queued.value; XCTFail() } catch { }
        XCTAssertEqual(vault.calls, [1, 0, 0]); let calls = await transport.calls; XCTAssertEqual(calls, 0)
    }
    @Test func testSeparateLaunchDoesNotInheritSavedConsent() async throws {
        let vault = VaultSpy(); let transport = TransportSpy()
        let first = CredentialBroker(vault: vault, transport: transport)
        try first.connect(.codex, credential: AccessCredential(token: token(.codex)))
        let nextLaunch = CredentialBroker(vault: vault, transport: transport)
        do { _ = try await nextLaunch.fetch(.codex); XCTFail() } catch { }
        XCTAssertEqual(vault.calls, [1, 0, 0])
    }
}

struct PolicyTests {
    @Test func testOnlyExactProviderEndpointsAndIntendedMethodsReceiveSyntheticSecrets() throws {
        for provider in Provider.allCases.filter(\.supportsLive) {
            let credential = try AccessCredential(token: token(provider), accountID: "test-account")
            let request = try UsageRequestPolicy.request(provider: provider, credential: credential)
            XCTAssertEqual(request.url, provider.endpoint)
            XCTAssertEqual(request.httpMethod, provider == .gemini ? "POST" : "GET")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer \(token(provider))")
            XCTAssertFalse(request.url!.absoluteString.contains(syntheticToken))
            XCTAssertNil(request.value(forHTTPHeaderField: "Cookie"))
            XCTAssertFalse(request.httpShouldHandleCookies)
            if provider == .gemini { XCTAssertEqual(try JSONSerialization.jsonObject(with: request.httpBody!) as? [String: String], ["project": "test-account"]) }
            for bad in ["http://api.anthropic.com/api/oauth/usage", "https://api.anthropic.com.evil.test/api/oauth/usage", provider.endpoint!.absoluteString + "?token=x", provider.endpoint!.absoluteString + "#fragment", "https://evil.test/", "https://api.anthropic.com:443/api/oauth/usage", "https://user@api.anthropic.com/api/oauth/usage"] {
                XCTAssertFalse(UsageRequestPolicy.permits(URL(string: bad)!, for: provider))
            }
        }
    }
    @Test func testProviderEnrollmentRejectsApiKeysPasswordShapesAndWrongProviderTokens() throws {
        for provider in Provider.allCases.filter(\.supportsLive) {
            for bad in ["AIzaSySYNTHETIC-API-KEY-1234567890", "sk-generic-api-key-1234567890", "passwordButLongEnoughToPassOldCheck123", "{\"access_token\":\"secret\"}"] {
                XCTAssertThrowsError(try AccessCredential(token: bad, accountID: "test-project").validate(for: provider))
            }
        }
        XCTAssertThrowsError(try AccessCredential(token: token(.gemini), accountID: "test-project").validate(for: .claude))
    }
    @Test func testNoCacheCookiesOrCredentialStorage() {
        let config = UsageRequestPolicy.configuration()
        XCTAssertNil(config.urlCache); XCTAssertNil(config.httpCookieStorage); XCTAssertNil(config.urlCredentialStorage)
        XCTAssertFalse(config.httpShouldSetCookies)
        XCTAssertEqual(config.requestCachePolicy, .reloadIgnoringLocalCacheData)
    }
    @Test func testSameAndCrossHostRedirectsAreUnconditionallyRejected() {
        let delegate = NoRedirectDelegate()
        let session = URLSession(configuration: .ephemeral)
        defer { session.invalidateAndCancel() }
        let task = session.dataTask(with: Provider.claude.endpoint!) // never resumed
        for target in [Provider.claude.endpoint!, URL(string: "https://evil.test/steal")!] {
            let done = CallbackFlag()
            delegate.urlSession(session, task: task, willPerformHTTPRedirection: HTTPURLResponse(url: Provider.claude.endpoint!, statusCode: 302, httpVersion: nil, headerFields: nil)!, newRequest: URLRequest(url: target)) { request in
                XCTAssertNil(request); done.mark()
            }
            #expect(done.called)
        }
    }
    @Test func testSecretDescriptionsAndFailuresAreRedacted() throws {
        let credential = try AccessCredential(token: syntheticToken)
        XCTAssertFalse(String(describing: credential).contains(syntheticToken))
        XCTAssertFalse(String(reflecting: credential).contains(syntheticToken))
        for error in [SafeError.network, .credentials, .response, .unauthorized] { XCTAssertFalse(error.localizedDescription.contains(syntheticToken)) }
        XCTAssertThrowsError(try AccessCredential(token: syntheticToken + "\r\nCookie: leaked"))
        XCTAssertThrowsError(try AccessCredential(token: syntheticToken, accountID: "x\nAuthorization: leaked"))
    }
}

struct ParserTests {
    @Test func testClaudeMissingWindowIsNotZeroAndOnlyNumericQuotaLeavesDecoder() throws {
        let data = Data(#"{"five_hour":{"utilization":27.5,"resets_at":"2026-09-22T12:00:00Z"},"seven_day":null,"accessToken":"synthetic-DO-NOT-RETURN","email":"private@example.test"}"#.utf8)
        let result = try QuotaDecoder.decode(data, provider: .claude)
        XCTAssertEqual(result.windows.count, 1); XCTAssertEqual(result.windows[0].usedPercent, 27.5)
        XCTAssertFalse(String(reflecting: result).contains("DO-NOT-RETURN")); XCTAssertFalse(String(reflecting: result).contains("private@example"))
        XCTAssertThrowsError(try QuotaDecoder.decode(Data("{}".utf8), provider: .claude))
        XCTAssertThrowsError(try QuotaDecoder.decode(Data(#"{"five_hour":{"utilization":true}}"#.utf8), provider: .claude))
    }
    @Test func testCodexUsesReportedWindowsAndResetNotInventedQuota() throws {
        let result = try QuotaDecoder.decode(Data(#"{"rate_limit":{"primary_window":{"used_percent":42,"reset_after_seconds":60},"secondary_window":{"used_percent":85}}}"#.utf8), provider: .codex, now: Date(timeIntervalSince1970: 1000))
        XCTAssertEqual(result.windows.map(\.usedPercent), [42,85]); XCTAssertEqual(result.windows[0].resetsAt, Date(timeIntervalSince1970: 1060)); XCTAssertNil(result.windows[1].resetsAt)
    }
    @Test func testGeminiModelBucketsConservativelySelectMostConstrained() throws {
        let result = try QuotaDecoder.decode(Data(#"{"buckets":[{"modelId":"gemini-2.5-pro","remainingFraction":0.75},{"modelId":"gemini-2.5-pro","remainingFraction":0.5},{"modelId":"gemini-2.5-flash","remainingFraction":1},{"modelId":"secret@example.test","remainingFraction":0.3}]}"#.utf8), provider: .gemini)
        XCTAssertEqual(result.windows.count, 2); XCTAssertEqual(result.windows.first(where: { $0.id == "gemini-2.5-pro" })?.usedPercent, 50)
        XCTAssertThrowsError(try QuotaDecoder.decode(Data(#"{"buckets":[]}"#.utf8), provider: .gemini))
        XCTAssertThrowsError(try QuotaDecoder.decode(Data(#"{"buckets":[{"modelId":"gemini-test","remainingFraction":1.5}]}"#.utf8), provider: .gemini))
    }
    @Test func testBoundedResponsesAndInvalidPercent() {
        XCTAssertThrowsError(try QuotaDecoder.decode(Data(repeating: 32, count: QuotaDecoder.maxBytes + 1), provider: .codex))
        XCTAssertThrowsError(try QuotaDecoder.decode(Data(#"{"five_hour":{"utilization":-1}}"#.utf8), provider: .claude))
    }
    @Test func testDisabledLocalImportDoesNotReadAndStrictSchemaRejectsSecrets() throws {
        var reads = 0
        XCTAssertThrowsError(try AggregateImporter.load(provider: .claude, enabled: false) { reads += 1; return Data() })
        XCTAssertEqual(reads, 0)
        let json = #"[{"id":"one","provider":"claude","date":"2026-09-21","model":"claude-test","inputTokens":100,"cachedInputTokens":20,"outputTokens":30}]"#
        let rows = try AggregateImporter.load(provider: .claude, enabled: true) { Data(json.utf8) }
        XCTAssertEqual(rows[0].totalTokens, 150); XCTAssertEqual(rows[0].estimate(inputRate: 1, cachedRate: 0.1, outputRate: 5), 0.000252, accuracy: 0.0000001)
        for invalid in [json.replacingOccurrences(of: "2026-09-21", with: "2026-02-31"), json.replacingOccurrences(of: "\"id\":", with: "\"accessToken\":\"secret\",\"id\":"), json.replacingOccurrences(of: "\"claude\"", with: "\"codex\"")] {
            XCTAssertThrowsError(try AggregateImporter.load(provider: .claude, enabled: true) { Data(invalid.utf8) })
        }
    }
}

private final class CallbackFlag: @unchecked Sendable {
    private let lock = NSLock()
    private var value = false
    var called: Bool { lock.withLock { value } }
    func mark() { lock.withLock { value = true } }
}
private func XCTAssertEqual<T: Equatable>(_ lhs: T, _ rhs: T) { #expect(lhs == rhs) }
private func XCTAssertEqual(_ lhs: Double, _ rhs: Double, accuracy: Double) { #expect(abs(lhs - rhs) <= accuracy) }
private func XCTAssertFalse(_ value: Bool) { #expect(!value) }
private func XCTAssertNil<T>(_ value: T?) { #expect(value == nil) }
private func XCTFail(_ message: String = "Unexpected success") { Issue.record(Comment(rawValue: message)) }
private func XCTAssertThrowsError<T>(_ body: @autoclosure () throws -> T) {
    do { _ = try body(); Issue.record("Expected an error") } catch { }
}
