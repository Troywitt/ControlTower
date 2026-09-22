import Foundation
import Security
import LocalAuthentication
import LocalUsageCore

/// Only this app's own service/accounts. Never query provider CLI credentials.
struct KeychainVault: CredentialVault {
    private let service = "com.bodie.controltower.private.access-tokens.v1"
    private func query(_ provider: Provider) -> [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: service,
         kSecAttrAccount as String: provider.rawValue,
         kSecAttrSynchronizable as String: false]
    }
    func save(_ credential: AccessCredential, for provider: Provider) throws {
        // Credential encoding is limited to the Keychain boundary. No file fallback.
        let data = try credential.keychainRepresentation()
        let status = SecItemUpdate(query(provider) as CFDictionary, [kSecValueData as String: data] as CFDictionary)
        if status == errSecItemNotFound {
            var add = query(provider)
            add[kSecValueData as String] = data
            add[kSecAttrLabel as String] = "ControlTower Private — \(provider.title) access token"
            // macOS login Keychain uses the signed app's default access control.
            guard SecItemAdd(add as CFDictionary, nil) == errSecSuccess else { throw SafeError.credentials }
        } else if status != errSecSuccess { throw SafeError.credentials }
    }
    func load(for provider: Provider) throws -> AccessCredential {
        var read = query(provider)
        read[kSecReturnData as String] = true
        read[kSecMatchLimit as String] = kSecMatchLimitOne
        // Reads never trigger background authentication dialogs. Reconnect explicitly.
        let context = LAContext()
        context.interactionNotAllowed = true
        read[kSecUseAuthenticationContext as String] = context
        var result: CFTypeRef?
        guard SecItemCopyMatching(read as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else { throw SafeError.credentials }
        return try AccessCredential.fromKeychainRepresentation(data)
    }
    func remove(for provider: Provider) throws {
        let status = SecItemDelete(query(provider) as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else { throw SafeError.credentials }
    }
}
