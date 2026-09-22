// swift-tools-version: 6.0
import PackageDescription

// Deliberately isolated from the historical upstream Sources/ControlTower* trees.
let package = Package(
    name: "ControlTowerLocal",
    platforms: [.macOS(.v14)],
    products: [.executable(name: "ControlTowerLocal", targets: ["ControlTowerLocal"])],
    dependencies: [],
    targets: [
        .target(name: "LocalUsageCore"),
        .executableTarget(name: "ControlTowerLocal", dependencies: ["LocalUsageCore"]),
        .testTarget(name: "LocalUsageCoreTests", dependencies: ["LocalUsageCore"]),
    ]
)
