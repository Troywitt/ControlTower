import Foundation

public enum UsageRequestPolicy {
    public static func permits(_ url: URL, for provider: Provider) -> Bool {
        // Exact string equality also excludes alternate ports, credentials, fragments,
        // encoded paths and attacker-controlled query parameters.
        url.absoluteString == provider.endpoint?.absoluteString
    }
    public static func request(provider: Provider, credential: AccessCredential) throws -> URLRequest {
        try credential.validate(for: provider)
        guard let endpoint = provider.endpoint else { throw SafeError.unsupported }
        var request = URLRequest(url: endpoint, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 20)
        request.httpMethod = "GET"
        request.httpShouldHandleCookies = false
        request.setValue("Bearer \(credential.token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("ControlTowerPrivate/1", forHTTPHeaderField: "User-Agent")
        if provider == .claude { request.setValue("oauth-2025-04-20", forHTTPHeaderField: "anthropic-beta") }
        if provider == .codex, let account = credential.accountID { request.setValue(account, forHTTPHeaderField: "ChatGPT-Account-Id") }
        if provider == .gemini {
            guard let project = credential.accountID else { throw SafeError.project }
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONSerialization.data(withJSONObject: ["project": project])
        }
        return request
    }
    public static func configuration() -> URLSessionConfiguration {
        let config = URLSessionConfiguration.ephemeral
        config.urlCache = nil
        config.httpCookieStorage = nil
        config.httpShouldSetCookies = false
        config.urlCredentialStorage = nil
        config.requestCachePolicy = .reloadIgnoringLocalCacheData
        config.timeoutIntervalForRequest = 20
        config.timeoutIntervalForResource = 30
        return config
    }
}

final class NoRedirectDelegate: NSObject, URLSessionTaskDelegate, Sendable {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping @Sendable (URLRequest?) -> Void) {
        // Deny ALL redirects, including same host. Never forward bearer credentials.
        completionHandler(nil)
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, didReceive challenge: URLAuthenticationChallenge,
                    completionHandler: @escaping @Sendable (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        if challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust {
            completionHandler(.performDefaultHandling, nil) // normal system TLS validation
        } else {
            completionHandler(.cancelAuthenticationChallenge, nil) // no password/cert lookup
        }
    }
}

public struct RestrictedUsageTransport: QuotaTransport {
    private let configuration: @Sendable () -> URLSessionConfiguration
    public init() { configuration = UsageRequestPolicy.configuration }
    // Test-only injection is internal, never configured from user data or environment.
    init(configuration: @escaping @Sendable () -> URLSessionConfiguration) { self.configuration = configuration }
    public func fetch(provider: Provider, credential: AccessCredential) async throws -> QuotaSnapshot {
        let request = try UsageRequestPolicy.request(provider: provider, credential: credential)
        guard let url = request.url, UsageRequestPolicy.permits(url, for: provider) else { throw SafeError.network }
        let session = URLSession(configuration: configuration(), delegate: NoRedirectDelegate(), delegateQueue: nil)
        defer { session.invalidateAndCancel() }
        do {
            try Task.checkCancellation()
            let (bytes, response) = try await session.bytes(for: request)
            guard let http = response as? HTTPURLResponse,
                  let finalURL = http.url, UsageRequestPolicy.permits(finalURL, for: provider) else { throw SafeError.response }
            switch http.statusCode {
            case 200: break
            case 401, 403: throw SafeError.unauthorized
            case 429: throw SafeError.rateLimited
            default: throw SafeError.network
            }
            if response.expectedContentLength > QuotaDecoder.maxBytes { throw SafeError.tooLarge }
            var data = Data()
            for try await byte in bytes {
                try Task.checkCancellation()
                guard data.count < QuotaDecoder.maxBytes else { throw SafeError.tooLarge }
                data.append(byte)
            }
            return try QuotaDecoder.decode(data, provider: provider)
        } catch let error as SafeError { throw error }
        catch { throw SafeError.network } // Never log/return URLSession descriptions or raw body.
    }
}
