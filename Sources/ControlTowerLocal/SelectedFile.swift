import Foundation
import Darwin
import LocalUsageCore

/// Bounded read of exactly the selected regular file; no symlinks, folders or bookmarks.
enum SelectedFile {
    static func read(_ url: URL) throws -> Data {
        guard url.isFileURL, url.pathExtension.lowercased() == "json" else { throw SafeError.format }
        let granted = url.startAccessingSecurityScopedResource()
        defer { if granted { url.stopAccessingSecurityScopedResource() } }
        let fd = open(url.path, O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
        guard fd >= 0 else { throw SafeError.file }
        defer { close(fd) }
        var metadata = stat()
        guard fstat(fd, &metadata) == 0, (metadata.st_mode & S_IFMT) == S_IFREG else { throw SafeError.file }
        guard metadata.st_size <= AggregateImporter.maxBytes else { throw SafeError.tooLarge }
        var result = Data()
        var buffer = [UInt8](repeating: 0, count: 65536)
        while true {
            let count = Darwin.read(fd, &buffer, buffer.count)
            if count == 0 { break }
            guard count > 0 else { throw SafeError.file }
            guard result.count + count <= AggregateImporter.maxBytes else { throw SafeError.tooLarge }
            result.append(contentsOf: buffer.prefix(count))
        }
        return result
    }
}
