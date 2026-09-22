import Foundation

// Only the platform Keychain adapter uses these. Deliberately not part of UI view state.
extension AccessCredential {
    private struct Stored: Codable { let token: String; let accountID: String? }
    public func keychainRepresentation() throws -> Data {
        try JSONEncoder().encode(Stored(token: token, accountID: accountID))
    }
    public static func fromKeychainRepresentation(_ data: Data) throws -> AccessCredential {
        guard data.count <= 32768, let stored = try? JSONDecoder().decode(Stored.self, from: data) else { throw SafeError.credentials }
        return try AccessCredential(token: stored.token, accountID: stored.accountID)
    }
}
