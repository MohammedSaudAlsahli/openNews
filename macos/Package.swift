// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "OpenStudio",
    platforms: [.macOS(.v14)],
    products: [.executable(name: "OpenStudio", targets: ["OpenStudioApp"])],
    targets: [
        .executableTarget(name: "OpenStudioApp", resources: [.process("Resources")]),
        .testTarget(name: "OpenStudioAppTests", dependencies: ["OpenStudioApp"])
    ],
    swiftLanguageModes: [.v5]
)
