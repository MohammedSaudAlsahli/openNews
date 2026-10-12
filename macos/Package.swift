// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "EditorialIntelligenceStudio",
    platforms: [.macOS(.v14)],
    products: [.executable(name: "EditorialIntelligenceStudio", targets: ["EISApp"])],
    targets: [
        .executableTarget(name: "EISApp", resources: [.process("Resources")]),
        .testTarget(name: "EISAppTests", dependencies: ["EISApp"])
    ],
    swiftLanguageModes: [.v5]
)
