import Foundation

public protocol CredentialVault: Sendable {
    func save(_ credential: AccessCredential, for provider: Provider) throws
    func load(for provider: Provider) throws -> AccessCredential
    func remove(for provider: Provider) throws
}
public protocol QuotaTransport: Sendable {
    func fetch(provider: Provider, credential: AccessCredential) async throws -> QuotaSnapshot
}

/// Explicit consent gate and short-lived credential handling. Same-process encapsulation,
/// NOT an OS-isolated helper. No startup availability checks or fallback credential sources.
@MainActor
public final class CredentialBroker {
    private let vault: any CredentialVault
    private let transport: any QuotaTransport
    private var enabled: Set<Provider> = []
    private var generations: [Provider: Int] = [:]
    private var pending: [Provider: Task<QuotaSnapshot, Error>] = [:]
    public init(vault: any CredentialVault, transport: any QuotaTransport) {
        self.vault = vault; self.transport = transport
    }
    public func connect(_ provider: Provider, credential: AccessCredential) throws {
        guard provider.supportsLive else { throw SafeError.unsupported }
        try credential.validate(for: provider)
        disable(provider)
        do { try vault.save(credential, for: provider) } catch { throw SafeError.credentials }
        enabled.insert(provider)
    }
    /// Called only by an explicit user action, never inferred from a saved preference.
    public func enableSaved(_ provider: Provider) { if provider.supportsLive { enabled.insert(provider) } }
    public func disable(_ provider: Provider) {
        enabled.remove(provider)
        generations[provider, default: 0] += 1
        pending.removeValue(forKey: provider)?.cancel()
    }
    public func removeSaved(_ provider: Provider) throws {
        guard provider.supportsLive else { throw SafeError.unsupported }
        disable(provider)
        do { try vault.remove(for: provider) } catch { throw SafeError.credentials }
    }
    public func isEnabled(_ provider: Provider) -> Bool { enabled.contains(provider) }
    public func fetch(_ provider: Provider) async throws -> QuotaSnapshot {
        // This check must precede every credential and network operation.
        guard !Task.isCancelled else { throw SafeError.disabled }
        guard provider.supportsLive else { throw SafeError.unsupported }
        guard enabled.contains(provider) else { throw SafeError.disabled }
        if pending[provider] != nil { throw SafeError.disabled } // UI coalesces refreshes; do not hand out an unguarded in-flight result.
        let credential: AccessCredential
        do { credential = try vault.load(for: provider); try credential.validate(for: provider) }
        catch { disable(provider); throw SafeError.credentials }
        let generation = generations[provider, default: 0]
        let transport = self.transport
        let task = Task {
            guard !Task.isCancelled else { throw SafeError.disabled }
            return try await transport.fetch(provider: provider, credential: credential) }
        pending[provider] = task
        do {
            let result = try await task.value
            guard enabled.contains(provider), generations[provider, default: 0] == generation else { throw SafeError.disabled }
            pending[provider] = nil
            return result
        } catch {
            guard generations[provider, default: 0] == generation else { throw SafeError.disabled }
            pending[provider] = nil
            let safe = error as? SafeError ?? .network
            // Fail closed: no retry loops or Keychain prompt storms on any failure.
            disable(provider)
            throw safe
        }
    }
}
