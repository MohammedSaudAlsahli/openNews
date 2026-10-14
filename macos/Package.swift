// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "OpenStudio",
    platforms: [.macOS(.v14)],
    products: [.executable(name: "OpenStudio", targets: ["OpenStudioApp"])],
    dependencies: [.package(url: "https://github.com/sparkle-project/Sparkle", exact: "2.10.0")],
    targets: [
        .executableTarget(name: "OpenStudioApp", dependencies: [.product(name: "Sparkle", package: "Sparkle")], resources: [.process("Resources")]),
        .testTarget(name: "OpenStudioAppTests", dependencies: ["OpenStudioApp"])
    ],
    swiftLanguageModes: [.v5]
)
