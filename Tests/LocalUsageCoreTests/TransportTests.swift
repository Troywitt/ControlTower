import Foundation
import Testing
@testable import LocalUsageCore

private final class MockHTTPState: @unchecked Sendable {
    private let lock = NSLock()
    private var code = 200
    private var body = Data()
    private var seen: [URLRequest] = []
    func configure(status: Int, data: Data) { lock.withLock { code = status; body = data; seen = [] } }
    func response(_ request: URLRequest) -> (Int, Data) { lock.withLock { seen.append(request); return (code, body) } }
    var requests: [URLRequest] { lock.withLock { seen } }
}
private final class MockHTTP: URLProtocol, @unchecked Sendable {
    static let state = MockHTTPState()
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        let (status, data) = Self.state.response(request)
        let response = HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: "HTTP/1.1", headerFields: ["Content-Type": "application/json"])!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: data)
        client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}

@Suite(.serialized)
struct TransportTests {
    private func transport() -> RestrictedUsageTransport {
        RestrictedUsageTransport {
            let config = UsageRequestPolicy.configuration()
            config.protocolClasses = [MockHTTP.self] // All URLs intercepted; no sockets.
            return config
        }
    }
    @Test func syntheticTokenOnlyReachesSelectedProviderRequest() async throws {
        let synthetic = "sk-ant-oat01-SYNTHETIC-TRANSPORT-ONLY-123456"
        MockHTTP.state.configure(status: 200, data: Data(#"{"five_hour":{"utilization":15}}"#.utf8))
        let result = try await transport().fetch(provider: .claude, credential: AccessCredential(token: synthetic))
        #expect(result.windows[0].usedPercent == 15)
        #expect(MockHTTP.state.requests.count == 1)
        #expect(MockHTTP.state.requests[0].url == Provider.claude.endpoint)
        #expect(MockHTTP.state.requests[0].value(forHTTPHeaderField: "Authorization") == "Bearer \(synthetic)")
        #expect(!String(reflecting: result).contains(synthetic))
    }
    @Test func rawBodiesAndRedirectStatusesNeverReachErrorsOrTriggerSecondRequest() async throws {
        let synthetic = "sk-ant-oat01-SYNTHETIC-TRANSPORT-ONLY-123456"
        for code in [301, 302, 307, 308, 401, 403, 429, 500] {
            MockHTTP.state.configure(status: code, data: Data("leaked-token=\(synthetic)".utf8))
            do {
                _ = try await transport().fetch(provider: .claude, credential: AccessCredential(token: synthetic))
                Issue.record("Unexpected success")
            } catch {
                #expect(error is SafeError)
                #expect(!error.localizedDescription.contains(synthetic))
                #expect(!String(reflecting: error).contains(synthetic))
            }
            #expect(MockHTTP.state.requests.count == 1)
        }
    }
    @Test func oversizedAndMalformedBodiesAreRejectedWithoutEcho() async throws {
        let credential = try AccessCredential(token: "sk-ant-oat01-SYNTHETIC-TRANSPORT-ONLY-123456")
        for data in [Data(repeating: 65, count: QuotaDecoder.maxBytes + 1), Data("secret raw provider text".utf8)] {
            MockHTTP.state.configure(status: 200, data: data)
            do { _ = try await transport().fetch(provider: .claude, credential: credential); Issue.record("Unexpected success") }
            catch { #expect(error is SafeError); #expect(!error.localizedDescription.contains("secret raw")) }
        }
    }
    @Test func geminiUsesExplicitProjectAndModelQuotaOnly() async throws {
        MockHTTP.state.configure(status: 200, data: Data(#"{"buckets":[{"modelId":"gemini-2.5-pro","remainingFraction":0.4}]}"#.utf8))
        let result = try await transport().fetch(provider: .gemini, credential: AccessCredential(token: "ya29.SYNTHETIC-TRANSPORT-ONLY-123456", accountID: "synthetic-project"))
        #expect(result.windows[0].usedPercent == 60)
        #expect(MockHTTP.state.requests.count == 1)
        #expect(MockHTTP.state.requests[0].url == Provider.gemini.endpoint)
        #expect(MockHTTP.state.requests[0].httpMethod == "POST")
    }
}
